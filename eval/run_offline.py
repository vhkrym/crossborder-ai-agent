import sys,argparse
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from eval.common import load_cases,isolated_database,run_case,write_report,ScriptedLLM,validate_evidence

def contract_checks(case,factory):
    checks=[]
    for fault,expected in [('timeout','llm_timeout'),('api','llm_api_error'),('json','llm_invalid_json'),('evidence','invalid_evidence_reference')]:
        row=run_case(case,ScriptedLLM(case,fault),factory)
        checks.append(dict(name=fault,passed=row['status']=='failed' and any(expected in e for e in row['errors'])))
    from app.tools.analytics_tools import build_tools
    tools=build_tools(factory)
    class Broken:
        def invoke(self,_):raise RuntimeError('SECRET_NOT_TO_LOG')
    tools['analyze_advertising']=Broken()
    mixed={**case,'expected_intent':'mixed','expected_agents':['profit','advertising'],'expected_tools':['analyze_profit','analyze_advertising']}
    with patch('app.agents.supervisor_graph.build_tools',return_value=tools):
        row=run_case(mixed,ScriptedLLM(mixed),factory)
    checks.append(dict(name='tool_failure_isolation',passed=row['status']=='partial_failed' and row['evidence_valid'] is True))
    # Nonexistent SKU in the trusted store must fail rather than borrow another store's SKU.
    other={**case,'selected_sku':'DEMO-016','store_id':1}
    row=run_case(other,ScriptedLLM(other),factory)
    checks.append(dict(name='cross_store_sku_isolation',passed=row['status']=='failed' and 'tool_error' in row['error_categories']))
    from app.agents.supervisor_state import SupervisorState
    from app.agents.supervisor_graph import build_supervisor_graph
    from app.agents.reporting import render_report
    initial=SupervisorState(task_id='mutation',**{k:case[k] for k in ('store_id','user_query','start_date','end_date','selected_sku','window','safety_days')})
    state=SupervisorState.model_validate(build_supervisor_graph(ScriptedLLM(case),factory).invoke(initial.model_dump()))
    original=state.report.key_findings[0];state.report.key_findings[0]=original+' 999999.99'
    valid,count=validate_evidence(state,factory)
    checks.append(dict(name='numeric_mutation_rejected',passed=valid is False and count>0))
    checks.append(dict(name='read_only_tools',passed=all(r.parameters.store_id==case['store_id'] for r in state.tool_results.values())))
    return checks

def main():
    p=argparse.ArgumentParser(description='Offline contract checks, NOT LLM route accuracy.')
    p.add_argument('--case-id',action='append');p.add_argument('--limit',type=int);p.add_argument('--output',type=Path,default=Path('eval/results/offline'))
    p.add_argument('--dataset',choices=['v1','v2'],default='v1')
    args=p.parse_args();rows=[]
    from eval.common import DATASET,DATASET_V2
    dataset_path=DATASET_V2 if args.dataset=='v2' else DATASET
    with isolated_database() as factory:
        for case in load_cases(path=dataset_path,case_ids=args.case_id,limit=args.limit):rows.append(run_case(case,ScriptedLLM(case),factory))
        guards=contract_checks(load_cases(case_ids=['profit-02'])[0],factory)
    report=write_report(rows,args.output,'offline',dict(fake='prescribed oracle; not language understanding'),guards,dataset_path=dataset_path)
    passed=sum(r['status']==r['expected_status'] and r['predicted_intent']==r['expected_intent'] and set(r['predicted_agents'])==set(r['expected_agents']) and set(r['actual_tools'])==set(r['expected_tools']) and r['tool_violations']==0 and (r['evidence_valid'] is True or r['expected_intent']=='unsupported') for r in rows)
    print({'passed':passed,'failed':len(rows)-passed,'contract_checks_passed':sum(c['passed'] for c in guards),'contract_checks_total':len(guards),'report':str(args.output/'report.json')})
    if passed!=len(rows) or not all(c['passed'] for c in guards):raise SystemExit(1)
if __name__=='__main__':main()
