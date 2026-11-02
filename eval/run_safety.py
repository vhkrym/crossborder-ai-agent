"""Offline by default. Live paired experiment requires explicit future authorization."""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from eval.common import (ROOT, DATASET, DATASET_V2, load_cases, run_case, write_report,
                         isolated_database, ScriptedLLM)
from eval.safety import DATASET as SAFETY_DATASET, load_safety, PromptVariant, safety_metrics
from eval.live_selection import CallBudget


def main():
    parser=argparse.ArgumentParser(description='Safety contracts offline; live mode requires explicit opt-in and may incur charges.')
    parser.add_argument('--mode',choices=['offline','live'],default='offline')
    parser.add_argument('--allow-real-api',action='store_true')
    parser.add_argument('--expected-model',help='Explicit approved model; required for live A/B and checked before provider creation')
    parser.add_argument('--suite',choices=['safety','v1','v2','all','ab'],default='safety')
    parser.add_argument('--variant',choices=['baseline','candidate','both'],default='both')
    parser.add_argument('--output',type=Path,default=ROOT/'eval/results/safety-offline')
    args=parser.parse_args()
    if args.mode=='live' and not args.allow_real_api:parser.error('Live API disabled; requires --allow-real-api and prior user budget authorization')
    if args.mode=='live' and args.suite!='ab':parser.error('Live safety runs require the frozen mixed-source ab suite and shared budget')
    if args.suite=='ab':
        if args.variant!='both':parser.error('A/B suite requires both paired variants')
        from eval.safety_ab import run_ab
        run_ab(args.output,args.mode,expected_model=args.expected_model)
        return
    if args.output.exists():parser.error('Use a new output directory; existing first results cannot be overwritten')
    safety,manifest=load_safety()
    variants=['baseline','candidate'] if args.variant=='both' else [args.variant]
    suites=['safety','v1','v2'] if args.suite=='all' else [args.suite]
    rows_by_suite={'safety':safety}
    if 'v1' in suites:rows_by_suite['v1']=load_cases(DATASET)
    if 'v2' in suites:rows_by_suite['v2']=load_cases(DATASET_V2)
    paths={'safety':SAFETY_DATASET,'v1':DATASET,'v2':DATASET_V2}
    llm=None;metadata={}
    summary=[]
    with isolated_database() as factory:
        for suite in suites:
            cases=rows_by_suite[suite]
            for variant in variants:
                rows=[]
                budget=CallBudget(llm,60) if llm is not None else None
                for case in cases:
                    runner=PromptVariant(budget if budget else ScriptedLLM(case),variant)
                    row=run_case(case,runner,factory)
                    if suite=='safety':row.update(category=case['category'])
                    rows.append(row)
                    config=dict(metadata,variant=variant,prompt_sha256=runner.sha,case_ids=[c['case_id'] for c in cases],fake=args.mode=='offline',logical_calls_attempted=budget.calls if budget else None)
                    output=args.output/suite/variant
                    report=write_report(rows,output,args.mode,config,dataset_path=paths[suite])
                    report['safety_metrics']=safety_metrics(rows)
                    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
                    # Keep safety-specific rates visible beside ordinary strict metrics.
                    with (output/'report.md').open('a',encoding='utf-8') as f:
                        f.write('\n\nSafety metrics (offline oracle is not model effectiveness):\n```json\n'+json.dumps(report['safety_metrics'],indent=2)+'\n```\n')
                summary.append(dict(suite=suite,variant=variant,cases=len(rows),strict_match=report['metrics']['strict_agent_set_exact_match'],unsupported=report['metrics']['unsupported'],safety=report['safety_metrics']))
                print(summary[-1],flush=True)
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    if args.mode=='offline' and any(r['strict_match']!=1 or r['safety']['unsupported_tool_calls'] or r['safety']['unsupported_completed'] for r in summary):raise SystemExit(1)


if __name__=='__main__':main()
