import sys,json,hashlib,time,platform,re
from pathlib import Path
from datetime import datetime,timezone
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from pydantic import BaseModel,Field,ConfigDict
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.agents.supervisor_state import SupervisorState,RouteDecision
from app.agents.supervisor_graph import build_supervisor_graph,AGENT_TO_TOOL
from app.agents.reporting import collect,render_report
from app.db.session import build_engine
from app.demo.seed import seed_demo
from app.tools.analytics_tools import execute_analysis,AnalysisInput
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from eval.metrics import summarize

DATASET=ROOT/'eval/datasets/supervisor_cases.jsonl'
DATASET_V2=ROOT/'eval/datasets/supervisor_cases_v2.jsonl'

def dataset_metadata(path):
    path=Path(path).resolve()
    manifests={DATASET.resolve():'manifest.json',DATASET_V2.resolve():'manifest_v2.json',
               (ROOT/'eval/datasets/safety_routing_cases.jsonl').resolve():'safety_routing_manifest.json'}
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if path in manifests:
        manifest=json.loads((ROOT/'eval/datasets'/manifests[path]).read_text(encoding='utf-8'))
        if manifest['sha256']!=digest:raise ValueError('dataset changed; review labels and publish a new version')
        return manifest['version'],digest
    return 'custom',digest
class Case(BaseModel):
    model_config=ConfigDict(extra='forbid')
    case_id:str
    user_query:str
    store_id:int
    start_date:str
    end_date:str
    selected_sku:str|None=None
    window:int=30
    safety_days:int=7
    expected_intent:str
    expected_agents:list[str]
    acceptable_agent_sets:list[list[str]]|None=None
    expected_tools:list[str]
    expected_status:str
    tags:list[str]

def load_cases(path=DATASET,case_ids=None,limit=None):
    dataset_metadata(path)
    rows=[Case.model_validate_json(line).model_dump() for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]
    assert len({r['case_id'] for r in rows})==len(rows),'duplicate case ID'
    for r in rows:
        RouteDecision(intent=r['expected_intent'],selected_agents=r['expected_agents'],reason='annotation')
        if set(r['expected_tools'])!={AGENT_TO_TOOL[a] for a in r['expected_agents']}:raise ValueError('label tool mismatch')
        alternatives=r.get('acceptable_agent_sets') or [r['expected_agents']]
        if set(r['expected_agents']) not in [set(a) for a in alternatives]:raise ValueError('original agents must remain acceptable')
        for agents in alternatives:
            intent='unsupported' if not agents else agents[0] if len(agents)==1 else 'mixed'
            RouteDecision(intent=intent,selected_agents=agents,reason='acceptable annotation')
            if (not agents)!=(r['expected_intent']=='unsupported'):raise ValueError('unsupported must have only empty agents')
        SupervisorState(task_id=r['case_id'],**{k:r[k] for k in ('store_id','user_query','start_date','end_date','selected_sku','window','safety_days')})
    if case_ids:
        if set(case_ids)-{r['case_id'] for r in rows}:raise ValueError('unknown case_id')
        rows=[r for r in rows if r['case_id'] in case_ids]
    if limit is not None:
        if limit<1:raise ValueError('limit must be positive')
        rows=rows[:limit]
    return rows

@contextmanager
def isolated_database():
    with TemporaryDirectory(prefix='commerce-eval-') as tmp:
        path=Path(tmp)/'evaluation.db';e=build_engine('sqlite:///'+path.as_posix());seed_demo(e);e.dispose()
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        readonly=build_engine('sqlite:///file:'+path.as_posix()+'?mode=ro&uri=true')
        try:yield sessionmaker(bind=readonly)
        finally:
            readonly.dispose()
            if before!=hashlib.sha256(path.read_bytes()).hexdigest():raise RuntimeError('evaluation modified database')

class ScriptedLLM:
    """Oracle contract fixture, NOT a natural-language classifier."""
    def __init__(self,case,fault=None):self.case=case;self.fault=fault
    def invoke(self,messages):
        payload=json.loads(messages[-1].content)
        if self.fault=='timeout':raise TimeoutError('not persisted')
        if self.fault=='api':raise RuntimeError('not persisted')
        if self.fault=='json':return SimpleNamespace(content='invalid json')
        if 'evidence' not in payload:
            value=dict(intent=self.case['expected_intent'],selected_agents=self.case['expected_agents'],reason='prescribed offline contract')
        else:value=dict(evidence_ids=['forged'] if self.fault=='evidence' else list(payload['evidence'])[:20])
        return SimpleNamespace(content=json.dumps(value))

class ObservedLLM:
    def __init__(self,llm):self.llm=llm;self.usage=[];self.failures=0
    def invoke(self,messages):
        try:response=self.llm.invoke(messages)
        except Exception:
            self.failures+=1;self.usage.append(dict(input_tokens=None,output_tokens=None));raise
        usage=getattr(response,'usage_metadata',None) or {}
        metadata=getattr(response,'response_metadata',None) or {};legacy=metadata.get('token_usage') or {}
        self.usage.append(dict(input_tokens=usage.get('input_tokens',legacy.get('prompt_tokens')),output_tokens=usage.get('output_tokens',legacy.get('completion_tokens'))))
        return response

def validate_evidence(state,factory):
    if not state.report:return None,0
    trusted={}
    for name,result in state.tool_results.items():
        if result.data is None:continue
        actual=execute_analysis(name,result.parameters,factory)
        if actual.data!=result.data:return False,len(state.report.key_findings)
        trusted.update(collect(name.removeprefix('analyze_'),actual))
    try:
        # Rebuild from independently recomputed metrics, not mutable graph evidence.
        check=state.model_copy(update={'evidence':trusted})
        expected=render_report(check,state.report.evidence_ids)
        unequal=sum(a!=b for a,b in zip(expected.key_findings,state.report.key_findings))+abs(len(expected.key_findings)-len(state.report.key_findings))
        for field in ('suggested_actions','business_risks','evidence_and_limits','problem_understanding'):
            wanted=getattr(expected,field);actual=getattr(state.report,field)
            if wanted!=actual and re.findall(r'[-+]?\d+(?:\.\d+)?',str(wanted))!=re.findall(r'[-+]?\d+(?:\.\d+)?',str(actual)):unequal+=1
        return expected==state.report,unequal
    except Exception:return False,len(state.report.key_findings)

def run_case(case,llm,factory):
    observed=ObservedLLM(llm);started=time.perf_counter()
    state=SupervisorState(task_id=case['case_id'],**{k:case[k] for k in ('store_id','user_query','start_date','end_date','selected_sku','window','safety_days')})
    updates={};nodes=[];transitions=['pending']
    try:
        graph=build_supervisor_graph(observed,factory)
        for event in graph.stream(state.model_dump(),config={'recursion_limit':10},stream_mode='updates'):
            for node,values in event.items():
                nodes.append(node);updates.update(values)
                if 'execution_status' in values:transitions.append(values['execution_status'])
        state=SupervisorState.model_validate({**state.model_dump(),**updates})
    except Exception:
        state=state.model_copy(update={**updates,'execution_status':'failed','errors':list(updates.get('errors',[]))+['evaluation_graph_exception']})
        transitions.append('failed')
    latency=time.perf_counter()-started
    valid,unbound=validate_evidence(state,factory)
    actual=[t.tool for t in state.traces if t.tool]
    predicted=state.route.selected_agents if state.route else []
    allowed={AGENT_TO_TOOL[a] for a in predicted}
    violations=sum(tool not in allowed for tool in actual)
    state_errors=int(state.execution_status not in ('completed','partial_failed','failed','unsupported'))+int(state.execution_status=='completed' and bool(state.errors))+int(state.execution_status=='unsupported' and bool(actual))
    allowed_transitions={'pending':{'running','unsupported','failed'},'running':{'running','completed','partial_failed','failed'}}
    state_errors+=sum(b not in allowed_transitions.get(a,set()) for a,b in zip(transitions,transitions[1:]))
    state_errors+=len(nodes)-len(set(nodes))
    for trace in state.traces:
        p=trace.parameters
        if p and (p.store_id,p.start_date,p.end_date,p.selected_sku)!=(state.store_id,state.start_date,state.end_date,state.selected_sku):violations+=1
    errors=state.errors
    categories=[]
    if observed.failures or any('llm_' in error for error in errors):categories.append('model_error')
    if any(t.status=='failed' for t in state.tool_results.values()):categories.append('tool_error')
    if valid is False or any('evidence' in error for error in errors):categories.append('evidence_error')
    if not state.route or state.route.intent!=case['expected_intent'] or set(predicted)!=set(case['expected_agents']):categories.append('routing_error')
    scope=check_scope(case,state)
    return dict(acceptable_agent_sets=case.get('acceptable_agent_sets'),scope_integrity=scope,answer_completeness=None,nodes=nodes,state_transitions=transitions,case_id=case['case_id'],expected_intent=case['expected_intent'],expected_agents=case['expected_agents'],expected_tools=case['expected_tools'],expected_status=case['expected_status'],predicted_intent=state.route.intent if state.route else None,predicted_agents=predicted,route_received=state.route is not None,actual_tools=actual,status=state.execution_status,errors=errors,error_categories=categories,latency_seconds=latency,evidence_valid=valid,unsupported_numeric_assertions=unbound,tool_violations=violations,state_errors=state_errors,usage=observed.usage,model_call_failures=observed.failures)

def check_scope(case,state):
    keys=('store_id','start_date','end_date','selected_sku')
    expected=AnalysisInput(**{k:case[k] for k in keys})
    def same(value):return all(getattr(value,k)==getattr(expected,k) for k in keys)
    if not same(state):return False
    parameters=[t.parameters for t in state.traces if t.tool]
    parameters += [r.parameters for r in state.tool_results.values()]
    if any(p is None or not same(p) for p in parameters):return False
    if parameters:return True
    return True if state.execution_status=='unsupported' else None

def write_report(rows,output,mode,metadata=None,guards=None,dataset_path=DATASET):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    version,digest=dataset_metadata(dataset_path)
    data=dict(mode=mode,run_time=datetime.now(timezone.utc).isoformat(),dataset_version=version,dataset_sha256=digest,python=platform.python_version(),metadata=metadata or {},metrics=summarize(rows),cases=rows,offline_contract_checks=guards)
    (output/'report.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# '+mode+' evaluation','', 'Offline scripted routes are NOT live model accuracy.' if mode=='offline' else 'Live outcomes include failures in denominators.','', '```json',json.dumps(data['metrics'],ensure_ascii=False,indent=2),'```','','| Case | Status | Agents | Errors |','|---|---|---|---|']
    lines.extend('| '+r['case_id']+' | '+r['status']+' | '+','.join(r['predicted_agents'])+' | '+','.join(r['error_categories'])+' |' for r in rows)
    (output/'report.md').write_text(chr(10).join(lines),encoding='utf-8')
    return data
