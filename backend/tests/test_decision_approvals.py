from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select,func,text
from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient
import pytest
from app.db.session import build_engine
from app.db.init_db import init_db
from app.db.migrate_agent_tasks import migrate as task_migrate
from app.db.migrate_decisions import migrate as decision_migrate
from app.db.migrate_decision_approvals import migrate
from app.models import Store,SalesRecord
from app.models.agent_task import AgentTask
from app.models.decision import DecisionProposal
from app.models.decision_audit import DecisionAudit
from app.services.decision_approvals import ApprovalService
from app.api.v1.decision_approvals import get_approval_service
from app.main import create_app
from datetime import date

@pytest.fixture
def env(tmp_path):
    e=build_engine('sqlite:///'+(tmp_path/'reviews.db').as_posix());init_db(e);task_migrate(e);decision_migrate(e);migrate(e)
    f=sessionmaker(bind=e);id=str(uuid4())
    with f() as s:
        s.add_all([Store(id=i,name=str(i),marketplace='Amazon',market='US',currency='USD') for i in (1,2)]);s.flush()
        task=AgentTask(task_id=str(uuid4()),store_id=1,user_query='test',start_date=date(2026,1,1),end_date=date(2026,3,31),status='completed');s.add(task);s.flush()
        s.add(DecisionProposal(proposal_id=id,source_task_id=task.task_id,store_id=1,sku='X',proposal_type='profit_review',title='test',description='review',risk_level='high',suggested_action='review',evidence_json=dict(schema_version='1',generated_at='2026-01-01T00:00:00',store_id=1,source_task_id=task.task_id,start_date='2026-01-01',end_date='2026-03-31',tool='analyze_profit',metrics={}),limitations_json=[],status='pending_review'));s.commit()
    yield ApprovalService(f),id,e
    e.dispose()

def test_approve_and_immutable_audit(env):
    svc,id,e=env;r=svc.review(id,1,'approve','审核通过')
    assert r['proposal'].status=='approved' and r['audit'].reviewer_id=='local-demo-reviewer' and r['audit'].identity_source=='local_demo'
    assert r['audit'].from_status=='pending_review' and r['audit'].to_status=='approved'
    with pytest.raises(RuntimeError):svc.review(id,1,'approve','again')
    with pytest.raises(RuntimeError):svc.review(id,1,'reject','no')
    assert len(svc.audit(id,1))==1
    with svc.factory() as s:
        assert s.scalar(select(func.count()).select_from(SalesRecord))==0
        with pytest.raises(IntegrityError):s.execute(text('DELETE FROM decision_audits'))
    migrate(e);assert len(svc.audit(id,1))==1

def test_draft_submit_and_reject(env):
    svc,id,e=env
    with svc.factory() as s:row=s.get(DecisionProposal,id);row.status='draft';s.commit()
    with pytest.raises(RuntimeError):svc.review(id,1,'approve','no')
    assert svc.review(id,1,'submit','提交')['proposal'].status=='pending_review'
    with pytest.raises(ValueError):svc.review(id,1,'reject',' ')
    assert svc.review(id,1,'reject','成本证据需要复核')['proposal'].status=='rejected'
    assert len(svc.audit(id,1))==2

def test_concurrent_review(env):
    svc,id,e=env
    def run(action):
        try:svc.review(id,1,action,'test');return True
        except RuntimeError:return False
    with ThreadPoolExecutor(2) as pool:assert sum(pool.map(run,['approve','reject']))==1
    assert len(svc.audit(id,1))==1

def test_api_identity_scope_validation(env):
    svc,id,e=env;app=create_app();app.dependency_overrides[get_approval_service]=lambda:svc
    with TestClient(app) as c:
        url=f'/api/v1/decisions/{id}'
        assert c.post(url+'/approve',params={'store_id':2},json={'comment':'wrong store'}).status_code==404
        assert c.post(url+'/approve',params={'store_id':1},json={'comment':'x','reviewer_id':'AI'}).status_code==422
        assert c.post(url+'/reject',params={'store_id':1},json={'comment':' '}).status_code==422
        assert c.post(url+'/approve',params={'store_id':1},json={}).status_code==200
        assert c.post(url+'/approve',params={'store_id':1},json={}).status_code==409
        assert c.get(url+'/audit',params={'store_id':1}).json()[0]['identity_source']=='local_demo'
        assert c.patch(url+'/audit',json={}).status_code==405
        assert c.post('/api/v1/decisions/bad/approve',params={'store_id':1},json={}).status_code==404


def test_atomic_rollback_on_audit_failure(env):
    from sqlalchemy import event
    svc,id,e=env
    def broken(*args):raise RuntimeError('audit write failed')
    event.listen(DecisionAudit,'before_insert',broken)
    try:
        with pytest.raises(RuntimeError):svc.review(id,1,'approve','test')
    finally:event.remove(DecisionAudit,'before_insert',broken)
    with svc.factory() as s:assert s.get(DecisionProposal,id).status=='pending_review'
    assert svc.audit(id,1)==[]


def test_legacy_check_migration(tmp_path):
    from sqlalchemy.schema import CreateTable
    e=build_engine('sqlite:///'+(tmp_path/'legacy.db').as_posix());init_db(e);task_migrate(e)
    with e.begin() as c:
        c.exec_driver_sql('CREATE UNIQUE INDEX uq_task_store_identity ON agent_tasks(task_id,store_id)')
        ddl=str(CreateTable(DecisionProposal.__table__).compile(e)).replace("'draft','pending_review','approved','rejected'","'draft','pending_review'")
        c.exec_driver_sql(ddl)
    factory=sessionmaker(bind=e);pid=str(uuid4());tid=str(uuid4())
    with factory() as s:
        s.add(Store(id=1,name='legacy',marketplace='Amazon',market='US',currency='USD'));s.flush()
        s.add(AgentTask(task_id=tid,store_id=1,user_query='legacy',start_date=date(2026,1,1),end_date=date(2026,3,31),status='completed'));s.flush()
        s.add(DecisionProposal(proposal_id=pid,source_task_id=tid,store_id=1,sku='legacy',proposal_type='profit_review',title='preserve',description='legacy evidence',risk_level='high',suggested_action='review',evidence_json={'original':'preserve'},limitations_json=['keep'],status='pending_review'));s.commit()
    with e.connect() as c:before=c.execute(text('SELECT * FROM decision_proposals')).fetchall()
    migrate(e);migrate(e)
    with e.connect() as c:
        assert c.execute(text('SELECT * FROM decision_proposals')).fetchall()==before
        ddl=c.scalar(text("SELECT sql FROM sqlite_master WHERE name='decision_proposals'"))
        assert "'approved'" in ddl and c.scalar(text('PRAGMA foreign_keys'))==1
    e.dispose()
