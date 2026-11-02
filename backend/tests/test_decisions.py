from datetime import date
from uuid import uuid4
import pytest
from sqlalchemy import inspect,select,func
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.db.session import build_engine
from app.db.migrate_agent_tasks import migrate as tasks_migrate
from app.db.migrate_decisions import migrate
from app.demo.seed import seed_demo
from app.models.agent_task import AgentTask
from app.models.decision import DecisionProposal
from app.models import SalesRecord
from app.services.decisions import DecisionService
from app.agents.supervisor_graph import build_supervisor_graph
from app.agents.supervisor_state import SupervisorState
from app.schemas.agent_tasks import TaskTrace
from app.main import create_app
from app.api.v1.decisions import get_decision_service
from test_supervisor import FakeLLM

@pytest.fixture(scope='module')
def setup(tmp_path_factory):
    e=build_engine('sqlite:///'+(tmp_path_factory.mktemp('decisions')/'test.db').as_posix());seed_demo(e);tasks_migrate(e);migrate(e)
    f=sessionmaker(bind=e)
    # Reuse real deterministic graph with fake routing to all three experts.
    class All(FakeLLM):
        def invoke(self,messages):
            import json
            r=super().invoke(messages)
            if 'evidence' not in json.loads(messages[-1].content):
                r.content=json.dumps(dict(intent='mixed',selected_agents=['profit','advertising','inventory'],reason='test'))
            return r
    state=SupervisorState(task_id=str(uuid4()),store_id=1,user_query='经营分析',start_date='2026-01-01',end_date='2026-03-31')
    result=SupervisorState.model_validate(build_supervisor_graph(All('mixed'),f).invoke(state.model_dump()))
    with f() as s:
        s.add(AgentTask(task_id=state.task_id,store_id=1,user_query='经营分析',start_date=state.start_date,end_date=state.end_date,status='completed',selected_agents=result.route.selected_agents,intent='mixed',report_json=result.report.model_dump(mode='json'),trace_json=TaskTrace(route=result.route,tools=result.traces).model_dump(mode='json')));s.commit()
    yield DecisionService(f),state.task_id,e
    e.dispose()

def test_all_scenarios(setup):
    svc,id,e=setup
    result=svc.generate(id);pairs={(p.sku,p.proposal_type) for p in result['proposals']}
    for pair in [('DEMO-001','profit_review'),('DEMO-002','ad_budget_review'),('DEMO-003','replenishment_review'),('DEMO-004','overstock_review'),('DEMO-005','cost_change_review')]:assert pair in pairs
    for p in result['proposals']:
        assert p.store_id==1 and str(p.source_task_id)==id and p.evidence_json.store_id==1
        assert p.evidence_json.metrics['sku']==p.sku
    old={p.proposal_id for p in result['proposals']}
    again=svc.generate(id);assert again['reused'] and {p.proposal_id for p in again['proposals']}==old
    migrate(e);migrate(e)
    with svc.factory() as s:assert s.scalar(select(func.count()).select_from(SalesRecord))==2700

def test_invalid_task_scope_and_status(setup):
    svc,id,e=setup
    with svc.factory() as s:
        original=s.get(AgentTask,id)
        for status in ['queued','running','partial_failed','failed','unsupported','interrupted']:
            task=AgentTask(task_id=str(uuid4()),store_id=1,user_query='test',start_date=original.start_date,end_date=original.end_date,status=status,report_json=original.report_json,trace_json=original.trace_json)
            s.add(task);s.commit()
            with pytest.raises(ValueError):svc.generate(task.task_id)
            s.rollback()
            original=s.get(AgentTask,id)
        bad=AgentTask(task_id=str(uuid4()),store_id=2,user_query='test',start_date=original.start_date,end_date=original.end_date,status='completed',selected_agents=original.selected_agents,report_json=original.report_json,trace_json=original.trace_json)
        s.add(bad);s.commit();bad_id=bad.task_id
    with pytest.raises(ValueError):svc.generate(bad_id)

def test_api(setup):
    svc,id,e=setup;app=create_app();app.dependency_overrides[get_decision_service]=lambda:svc
    with TestClient(app) as c:
        r=c.post('/api/v1/decisions/generate',json={'source_task_id':id});assert r.status_code==200,r.text
        assert c.post('/api/v1/decisions/generate',json={'source_task_id':id,'store_id':2}).status_code==422
        page=c.get('/api/v1/decisions',params={'store_id':1,'proposal_type':'profit_review','page_size':1}).json();assert page['total']>=1 and len(page['items'])==1
        assert c.get('/api/v1/decisions/'+page['items'][0]['proposal_id']).status_code==200
        assert c.get('/api/v1/decisions/not-valid').status_code==404
        assert c.get('/api/v1/decisions',params={'store_id':2}).json()['total']==0

def test_null_and_missing_comparison():
    from app.analytics.decisions import evaluate
    from app.schemas.analytics import ProfitItem,AdvertisingItem
    p=ProfitItem(sku='X',quantity=0,gross_sales=0,refund_amount=0,net_revenue=0,purchase_cost=None,logistics_cost=None,platform_fees=None,ad_spend=0,contribution_profit=None,profit_margin=None,cost_increased=True,reasons=['missing_cost'])
    a=AdvertisingItem(sku='X',spend=0,attributed_sales=0,clicks=0,ad_orders=0,acos=None,roas=None,cpc=None,conversion_rate=None,reasons=['zero_clicks'])
    rows,skipped=evaluate({'profit':[p],'advertising':[a]})
    assert not rows and 'X:profit_unavailable' in skipped and 'X:cost_change_requires_historical_margin_comparison' in skipped


def test_empty_generation_frozen(setup):
    svc,id,e=setup
    state=SupervisorState(task_id=str(uuid4()),store_id=1,user_query='profit',start_date='2025-01-01',end_date='2025-01-31')
    result=SupervisorState.model_validate(build_supervisor_graph(FakeLLM('profit'),svc.factory).invoke(state.model_dump()))
    with svc.factory() as s:
        s.add(AgentTask(task_id=state.task_id,store_id=1,user_query='profit',start_date=state.start_date,end_date=state.end_date,status='completed',selected_agents=['profit'],report_json=result.report.model_dump(mode='json'),trace_json=TaskTrace(route=result.route,tools=result.traces).model_dump(mode='json')));s.commit()
    first=svc.generate(state.task_id);second=svc.generate(state.task_id)
    assert not first['proposals'] and not second['proposals'] and second['reused'] and first['skipped_reasons']==second['skipped_reasons']


def test_database_cross_store_proposal_rejected(setup):
    from sqlalchemy.exc import IntegrityError
    svc,id,e=setup
    with svc.factory() as s:
        row=DecisionProposal(proposal_id=str(uuid4()),source_task_id=id,store_id=2,sku='X',proposal_type='profit_review',title='test',description='test',risk_level='high',suggested_action='review',evidence_json={},limitations_json=[],status='pending_review')
        s.add(row)
        with pytest.raises(IntegrityError):s.commit()
