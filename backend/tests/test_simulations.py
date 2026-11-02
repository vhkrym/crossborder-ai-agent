from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select,func
from fastapi.testclient import TestClient
import pytest
from test_decision_approvals import env
from app.db.migrate_decision_simulations import migrate
from app.services.simulations import SimulationService
from app.services.simulation_engine import simulate,ACTIONS
from app.models.decision import DecisionProposal
from app.models.decision_audit import DecisionAudit
from app.models.decision_simulation import DecisionSimulation
from app.schemas.simulations import SimulationInput
from app.api.v1.simulations import get_simulation_service
from app.main import create_app

@pytest.fixture
def approved(env):
    approval,id,e=env;approval.review(id,1,'approve','test');migrate(e);migrate(e)
    return SimulationService(approval.factory),approval,id,e

def test_success_idempotent_concurrent(approved):
    svc,approval,id,e=approved
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(svc.create,[id,id]))
    assert len({r['simulation_id'] for r in results})==1 and sum(not r['reused'] for r in results)==1
    result=svc.get(results[0]['simulation_id']);assert result.status=='simulation_completed' and result.output_json.simulation_only is True
    assert str(result.input_snapshot_json.approval.audit_id)==str(result.approval_audit_id)
    assert not svc.execute(result.simulation_id)
    with svc.factory() as s:
        assert s.get(DecisionProposal,id).status=='approved'
        assert s.scalar(select(func.count()).select_from(DecisionAudit))==1
    migrate(e);assert svc.get(result.simulation_id).status=='simulation_completed'

@pytest.mark.parametrize('status',['draft','pending_review','rejected'])
def test_unapproved(env,status):
    approval,id,e=env;migrate(e)
    with approval.factory() as s:p=s.get(DecisionProposal,id);p.status=status;s.commit()
    with pytest.raises(ValueError):SimulationService(approval.factory).create(id)

@pytest.mark.parametrize('kind',list(ACTIONS))
def test_five_actions(approved,kind):
    svc,approval,id,e=approved
    with svc.factory() as s:p=s.get(DecisionProposal,id);p.proposal_type=kind;s.commit()
    result=svc.get(svc.create(id)['simulation_id'])
    assert result.output_json.action_type==ACTIONS[kind][0] and result.output_json.simulation_only
    assert '未调用' in ''.join(result.output_json.limitations)

def test_failure_interruption(approved):
    svc,approval,id,e=approved
    def broken(_):raise RuntimeError('SECRET')
    svc.runner=broken;r=svc.get(svc.create(id)['simulation_id']);assert r.status=='simulation_failed' and 'SECRET' not in r.model_dump_json()
    # Separate approved proposal for simulated process interruption.
    with svc.factory() as s:
        p=s.get(DecisionProposal,id)
        row=DecisionSimulation(simulation_id=str(uuid4()),proposal_id=id+'x',source_task_id=p.source_task_id,approval_audit_id=str(r.approval_audit_id),store_id=1,sku='X',proposal_type='profit_review',action_type='profit_review_ticket',status='pending',input_snapshot_json=r.input_snapshot_json.model_dump(mode='json'),limitations_json=[])
        # Cannot insert fabricated proposal FK: confirm DB enforcement instead.
        from sqlalchemy.exc import IntegrityError
        s.add(row)
        with pytest.raises(IntegrityError):s.commit()
    assert svc.recover()==0

def test_api(approved):
    svc,approval,id,e=approved;app=create_app();app.dependency_overrides[get_simulation_service]=lambda:svc
    with TestClient(app) as c:
        url=f'/api/v1/decisions/{id}/simulate'
        assert c.post(url,json={'store_id':2}).status_code==422
        r=c.post(url,json={});assert r.status_code==200,r.text
        assert c.post(url,json={}).json()['reused']
        sid=r.json()['simulation_id'];assert c.get('/api/v1/simulations/'+sid).status_code==200
        assert c.get('/api/v1/simulations',params={'store_id':1,'page_size':1}).json()['total']==1
        assert c.get('/api/v1/simulations',params={'store_id':2}).json()['total']==0
        assert c.delete('/api/v1/simulations/'+sid).status_code==405
        assert c.patch('/api/v1/simulations/'+sid,json={}).status_code==405
        assert c.get('/api/v1/simulations/bad').status_code==404


@pytest.mark.parametrize('leftover',['pending','running'])
def test_real_interrupted_recovery(approved,leftover):
    svc,approval,id,e=approved
    class ProcessExit(BaseException):pass
    def crash(_):raise ProcessExit()
    svc.runner=crash
    with pytest.raises(ProcessExit):svc.create(id)
    with svc.factory() as session:
        row=session.scalar(select(DecisionSimulation));row.status=leftover;session.commit();sid=row.simulation_id
    assert svc.recover()==1 and svc.recover()==0
    assert svc.get(sid).status=='interrupted' and svc.create(id)['reused']


def test_invalid_snapshot_is_failed_not_running(approved):
    svc,approval,id,e=approved
    class Crash(BaseException):pass
    svc.runner=lambda _:(_ for _ in ()).throw(Crash())
    with pytest.raises(Crash):svc.create(id)
    with svc.factory() as s:
        row=s.scalar(select(DecisionSimulation));row.status='pending';row.input_snapshot_json={};s.commit();sid=row.simulation_id
    svc.execute(sid)
    with svc.factory() as s:assert s.get(DecisionSimulation,sid).status=='simulation_failed'
