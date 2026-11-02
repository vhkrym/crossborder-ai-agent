import sys,argparse,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from eval.common import load_cases,isolated_database,run_case,write_report

def main():
    p=argparse.ArgumentParser(description='Explicit opt-in real provider evaluation; may incur charges.')
    p.add_argument('--allow-real-api',action='store_true');p.add_argument('--case-id',action='append');p.add_argument('--limit',type=int);p.add_argument('--output',type=Path,default=Path('eval/results/live'))
    p.add_argument('--dataset',choices=['v1','v2'],default='v1')
    p.add_argument('--selection',type=Path,help='Frozen selection with adjacent .sha256; max 15 cases, no SDK retries.')
    args=p.parse_args()
    if not args.allow_real_api:p.error('Live API disabled; requires --allow-real-api')
    from eval.common import DATASET,DATASET_V2
    dataset_path=DATASET_V2 if args.dataset=='v2' else DATASET
    from eval.live_selection import load_selection,CallBudget
    if args.selection:
        if args.case_id or args.limit:p.error('selection cannot be combined with case-id or limit')
        if args.output.exists():p.error('frozen run requires a new output directory; no overwrite or resume')
        cases,selection_hash=load_selection(args.selection,dataset_path)
    else:cases=load_cases(path=dataset_path,case_ids=args.case_id,limit=args.limit)
    os.environ['LANGSMITH_TRACING']='false'
    os.environ['LANGCHAIN_TRACING_V2']='false'
    from app.agents.llm import create_llm,LLMSettings
    from urllib.parse import urlsplit
    try:
        settings=LLMSettings()
        if args.selection:settings=settings.model_copy(update={'llm_max_retries':0})
        llm=create_llm(settings)
    except Exception:p.error('LLM configuration invalid; no call made')
    rows=[]
    endpoint=urlsplit(settings.llm_base_url)
    metadata=dict(model=settings.llm_model,endpoint=f'{endpoint.scheme}://{endpoint.hostname}',timeout=settings.llm_timeout,max_retries=settings.llm_max_retries)
    if args.selection:
        llm=CallBudget(llm,75)
        metadata.update(selection_sha256=selection_hash,selected_case_ids=[c['case_id'] for c in cases],max_cases=15,max_logical_calls=75,token_or_cost_hard_cap=None)
    with isolated_database() as factory:
        for case in cases:
            rows.append(run_case(case,llm,factory))
            if args.selection:
                metadata['logical_calls_attempted']=llm.calls
                write_report(rows,args.output,'live',metadata,dataset_path=dataset_path)
            print({'case_id':case['case_id'],'status':rows[-1]['status'],'completed_cases':len(rows)},flush=True)
    report=write_report(rows,args.output,'live',metadata,dataset_path=dataset_path)
    print({'cases':len(rows),'report':str(args.output/'report.json'),'model_call_failures':report['metrics']['model_call_failures']})
if __name__=='__main__':main()
