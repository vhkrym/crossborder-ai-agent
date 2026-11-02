"""Explicit opt-in: sends demo analytics to configured provider and may incur costs."""
import argparse
import time
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy.orm import sessionmaker
from app.agents.llm import create_llm
from app.agents.supervisor_graph import build_supervisor_graph
from app.agents.supervisor_state import SupervisorState
from app.db.session import build_engine

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--allow-real-api',action='store_true');p.add_argument('--query',default='分析利润与广告风险')
    p.add_argument('--sku',default=None)
    args=p.parse_args()
    if not args.allow_real_api:p.error('requires --allow-real-api')
    path=Path(__file__).resolve().parents[1]/'demo.db'
    if not path.exists():p.error('demo.db missing; seed separately')
    e=build_engine('sqlite:///file:'+path.as_posix()+'?mode=ro&uri=true')
    started=time.monotonic()
    try:
        s=SupervisorState(task_id='smoke',store_id=1,user_query=args.query,start_date='2026-01-01',end_date='2026-03-31',selected_sku=args.sku)
        result=build_supervisor_graph(create_llm(),sessionmaker(bind=e)).invoke(s.model_dump(),config={'recursion_limit':10})
        output=SupervisorState.model_validate(result)
        from app.agents.reporting import render_report
        from app.tools.analytics_tools import execute_analysis
        matches={name:execute_analysis(name,value.parameters,sessionmaker(bind=e)).model_dump(mode='json')==value.model_dump(mode='json') for name,value in output.tool_results.items()}
        print(json.dumps(dict(status=output.execution_status,selected_agents=output.route.selected_agents if output.route else [],elapsed_seconds=round(time.monotonic()-started,2),errors=output.errors,tools={k:v.status for k,v in output.tool_results.items()},numeric_match=matches,evidence_valid=render_report(output,output.report.evidence_ids)==output.report if output.report else None,report=output.report.model_dump(mode='json') if output.report else None),ensure_ascii=False))
    finally:e.dispose()
if __name__=='__main__':main()
