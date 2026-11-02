from concurrent.futures import ThreadPoolExecutor
from datetime import date
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func, inspect
from fastapi.testclient import TestClient
import pytest
from app.db.session import build_engine
from app.db.init_db import init_db
from app.db.migrate_agent_tasks import migrate
from app.models import Store, Product
from app.models.agent_task import AgentTask
from app.services.agent_tasks import AgentTaskService
from app.schemas.agent_tasks import TaskCreate
from app.agents.supervisor_state import SupervisorState,RouteDecision,Report
from app.main import create_app
from app.api.v1.agent_tasks import get_task_service

BODY=dict(store_id=1,user_query='分析利润',start_date='2026-01-01',end_date='2026-03-31')
@pytest.fixture
def service(tmp_path):
    e=build_engine('sqlite:///'+(tmp_path/'tasks.db').as_posix());init_db(e)
    factory=sessionmaker(bind=e)
    with factory() as s:
        s.add_all([Store(id=i,name=str(i),marketplace='Amazon',market='US',currency='USD') for i in (1,2)]);s.commit()
    migrate(e)
    def runner(state,factory):
        state.route=RouteDecision(intent='profit',selected_agents=['profit'],reason='经营分析')
        state.execution_status='completed'
        state.report=Report(problem_understanding='利润分析',key_findings=['经验证的测试报告'],business_risks=[],suggested_actions=['建议人工复核，未执行'],evidence_and_limits=[],evidence_ids=[])
        return state.model_dump()
    yield AgentTaskService(factory,runner)
    e.dispose()

def test_migration_and_lifecycle(service):
    e=service.factory.kw['bind'];before=set(inspect(e).get_table_names());migrate(e);assert set(inspect(e).get_table_names())==before
    t=service.create(TaskCreate(**BODY));assert t.status=='queued'
    assert service.execute(t.task_id)
    assert not service.execute(t.task_id)
    result=service.get(t.task_id);assert result.status=='completed' and result.report_json
    assert result.started_at and result.finished_at and result.updated_at
    assert service.list(1,None,1,10)['total']==1
    with pytest.raises(LookupError):service.get(t.task_id,2)
    assert not service.finish(t.task_id,'failed')
    with pytest.raises(ValueError):service.finish(t.task_id,'running')

def test_concurrent_claim(service):
    t=service.create(TaskCreate(**BODY))
    with ThreadPoolExecutor(2) as pool:assert sum(pool.map(service.execute,[t.task_id,t.task_id]))==1

@pytest.mark.parametrize('status',['partial_failed','failed','unsupported'])
def test_terminal_states(service,status):
    original=service.runner
    def runner(state,factory):
        result=SupervisorState.model_validate(original(state,factory));result.execution_status=status
        if status=='failed':result.errors=['llm_timeout']
        return result.model_dump()
    service.runner=runner
    t=service.create(TaskCreate(**BODY));service.execute(t.task_id)
    assert service.get(t.task_id).status==status

def test_failure_and_recovery(service):
    def broken(*args):raise RuntimeError('Bearer TOP_SECRET')
    service.runner=broken
    t=service.create(TaskCreate(**BODY));service.execute(t.task_id)
    detail=service.get(t.task_id);assert detail.error_code=='execution_error' and 'TOP_SECRET' not in detail.model_dump_json()
    queued=service.create(TaskCreate(**BODY));running=service.create(TaskCreate(**BODY))
    with service.factory() as s:
        row=s.get(AgentTask,str(running.task_id));row.status='running';s.commit()
    assert service.recover()==2 and service.recover()==0
    assert service.get(queued.task_id).status=='interrupted' and not service.execute(running.task_id)

def test_api(service):
    app=create_app();app.dependency_overrides[get_task_service]=lambda:service
    with TestClient(app) as c:
        r=c.post('/api/v1/agent/tasks',json=BODY);assert r.status_code==202,r.text
        created=r.json();assert created['status']=='queued'
        detail=c.get('/api/v1/agent/tasks/'+created['task_id']);assert detail.status_code==200 and detail.json()['status']=='completed'
        assert 'report_json' in detail.json() and 'trace_json' in detail.json()
        assert c.get('/api/v1/agent/tasks/'+created['task_id'],params={'store_id':2}).status_code==404
        assert c.get('/api/v1/agent/tasks/00000000-0000-0000-0000-000000000000').status_code==404
        for invalid in [dict(store_id=99),dict(user_query=' '),dict(start_date='2027-01-01'),dict(status='completed'),dict(selected_sku='missing')]:
            expected=404 if 'store_id' in invalid or 'selected_sku' in invalid else 422
            assert c.post('/api/v1/agent/tasks',json=BODY|invalid).status_code==expected
        c.post('/api/v1/agent/tasks',json=BODY)
        page=c.get('/api/v1/agent/tasks',params={'store_id':1,'page_size':1}).json()
        assert len(page['items'])==1 and page['total']==2
        assert c.get('/api/v1/agent/tasks',params={'store_id':2}).json()['total']==0
        assert c.get('/api/v1/agent/tasks',params={'store_id':1,'page':0}).status_code==422


def test_real_graph_fake_llm_integration(service):
    from test_supervisor import FakeLLM
    from app.agents.supervisor_graph import build_supervisor_graph
    service.runner=lambda state,factory:build_supervisor_graph(FakeLLM('unsupported'),factory).invoke(state.model_dump())
    task=service.create(TaskCreate(**BODY));service.execute(task.task_id)
    detail=service.get(task.task_id)
    assert detail.status=='unsupported' and detail.trace_json.route.intent=='unsupported'


def test_readonly_worker_boundary_and_scrub(service,monkeypatch):
    from app.services.agent_tasks import scrub
    monkeypatch.setenv('LLM_API_KEY','TEST_SECRET_TOKEN')
    assert scrub({'x':'Bearer abc TEST_SECRET_TOKEN'})=={'x':'Bearer [REDACTED] [REDACTED]'}
    original=service.runner
    def runner(state,factory):
        # Independent session can commit during execution: no long-lived claim transaction.
        with factory() as s:
            row=s.get(AgentTask,state.task_id)
            assert row.status=='running'
        return original(state,factory)
    service.runner=runner
    t=service.create(TaskCreate(**BODY));service.execute(t.task_id)
    assert service.get(t.task_id).status=='completed'


def test_missing_llm_configuration_is_explicit_failure(service,monkeypatch):
    from app.services.agent_tasks import run_graph
    for key in ('LLM_BASE_URL','LLM_API_KEY','LLM_MODEL'):monkeypatch.setenv(key,'')
    service.runner=run_graph
    task=service.create(TaskCreate(**BODY));service.execute(task.task_id)
    result=service.get(task.task_id)
    assert result.status=='failed' and result.error_code=='llm_not_configured'
    assert result.report_json is None
