"""Mixed-source frozen pairing. Live execution requires a separate CLI opt-in."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from eval.common import ROOT,DATASET_V2,load_cases,dataset_metadata,ScriptedLLM,run_case,isolated_database
from eval.metrics import summarize
from eval.safety import DATASET as SAFETY_DATASET,load_safety,PromptVariant,prompt_config
from eval.ab_budget import SharedBudget,BudgetedArm
from app.tools.analytics_tools import AnalysisInput

SELECTION=ROOT/'eval/datasets/safety_ab_12.json'
INPUT_FIELDS=('store_id','user_query','start_date','end_date','selected_sku','window','safety_days')


def load_ab_selection(path=SELECTION):
    path=Path(path)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest!=path.with_suffix('.sha256').read_text(encoding='utf-8').split()[0]:raise ValueError('A/B selection SHA mismatch')
    selection=json.loads(path.read_text(encoding='utf-8'))
    safety,manifest=load_safety()
    sources={'eval/datasets/safety_routing_cases.jsonl':(SAFETY_DATASET,safety),
             'eval/datasets/supervisor_cases_v2.jsonl':(DATASET_V2,load_cases(DATASET_V2))}
    items=selection['samples'];cases=[]
    if len(items)!=12 or len({i['case_id'] for i in items})!=12:raise ValueError('must freeze 12 unique cases')
    counts={}
    for item in items:
        if item['source_dataset'] not in sources:raise ValueError('unapproved source')
        source,rows=sources[item['source_dataset']]
        if dataset_metadata(source)!=(item['source_version'],item['source_sha256']):raise ValueError('source version/hash mismatch')
        matches=[r for r in rows if r['case_id']==item['case_id']]
        if len(matches)!=1:raise ValueError('case not resolved')
        case=matches[0]
        if {k:case[k] for k in INPUT_FIELDS}!=item['trusted_input']:raise ValueError('trusted input snapshot changed')
        if {k:case[k] for k in ('expected_intent','expected_agents','expected_tools','expected_status')}!=item['labels']:raise ValueError('labels changed')
        AnalysisInput(**{k:v for k,v in item['trusted_input'].items() if k!='user_query'})
        known=item['case_id']=='unsupported-05'
        if item['known_regression_case']!=known:raise ValueError('incorrect regression provenance')
        if known:
            if source!=DATASET_V2 or item['category']!='execution':raise ValueError('known failure must be v2 execution')
        elif source!=SAFETY_DATASET or item['category']!=case['category']:raise ValueError('source/category mismatch')
        counts[item['category']]=counts.get(item['category'],0)+1
        cases.append({**case,'category':item['category'],'source_provenance':item})
    if counts!={'analysis':3,'advice':3,'execution':3,'mixed_execution':2,'injection':1}:raise ValueError('invalid strata')
    if selection['category_distribution']!=counts:raise ValueError('declared strata mismatch')
    if sum(c['case_id']=='unsupported-05' for c in cases)!=1:raise ValueError('missing original failure')
    for variant in ('baseline','candidate'):
        if prompt_config(variant)[1]!=selection['prompt_sha256'][variant]:raise ValueError('prompt snapshot mismatch')
    return cases,selection,digest


class OfflineUsage:
    """Explicit fake zero usage only for offline orchestration tests."""
    def __init__(self,case):self.llm=ScriptedLLM(case)
    def invoke(self,messages):
        response=self.llm.invoke(messages)
        return SimpleNamespace(content=response.content,usage_metadata={'input_tokens':0,'output_tokens':0})


def run_ab(output,mode='offline',expected_model=None):
    if mode not in ('offline','live'):raise ValueError('invalid mode')
    output=Path(output)
    if output.exists():raise ValueError('new result directory required')
    cases,selection,digest=load_ab_selection()
    llm=None;config=dict(mode=mode,selection_sha256=digest,prompt_sha256=selection['prompt_sha256'],fake=mode=='offline')
    if mode=='live':
        if not expected_model:raise ValueError('Live A/B requires an explicitly approved expected model')
        import os
        from urllib.parse import urlsplit
        from app.agents.llm import LLMSettings,create_llm
        os.environ['LANGSMITH_TRACING']='false';os.environ['LANGCHAIN_TRACING_V2']='false'
        try:
            settings=LLMSettings().model_copy(update={'llm_max_retries':0})
        except Exception:raise ValueError('LLM configuration invalid; no call made') from None
        if settings.llm_model!=expected_model:raise ValueError('Configured model differs from approved expected model; no call made')
        try:
            llm=create_llm(settings).bind(temperature=0)
        except Exception:raise ValueError('LLM configuration invalid; no call made') from None
        config.update(model=settings.llm_model,endpoint=urlsplit(settings.llm_base_url).hostname,temperature=0,timeout=settings.llm_timeout,max_retries=0)
    output.mkdir(parents=True)
    budget=SharedBudget();results={'baseline':[],'candidate':[]};pairs=[]
    def save():
        data=dict(config=config,budget=budget.snapshot(),calls=budget.records,pairs=pairs,
                  results={v:dict(cases=rows,metrics=summarize(rows)) for v,rows in results.items()},planned_cases_per_arm=12)
        # Null remaining arms are explicit; no automatic resume or replacement.
        (output/'paired_results.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        for variant,rows in results.items():
            (output/(variant+'.json')).write_text(json.dumps(dict(config=config,cases=rows,metrics=summarize(rows)),ensure_ascii=False,indent=2),encoding='utf-8')
    with isolated_database() as factory:
        for case in cases:
            pair=dict(case_id=case['case_id'],trusted_input={k:case[k] for k in INPUT_FIELDS},baseline=None,candidate=None)
            pairs.append(pair)
            for variant in ('baseline','candidate'):
                if budget.stop_reason:break
                arm=BudgetedArm(budget,llm or OfflineUsage(case),case['case_id'],variant)
                row=run_case(case,PromptVariant(arm,variant),factory)
                row.update(category=case['category'],source_provenance=case['source_provenance'])
                results[variant].append(row);pair[variant]=dict(status=row['status'],case_index=len(results[variant])-1)
                save()
            if budget.stop_reason:break
    present={p['case_id'] for p in pairs}
    pairs.extend(dict(case_id=c['case_id'],trusted_input={k:c[k] for k in INPUT_FIELDS},baseline=None,candidate=None) for c in cases if c['case_id'] not in present)
    save()
    print(dict(mode=mode,executed={v:len(rows) for v,rows in results.items()},budget=budget.snapshot()))
    return results,budget
