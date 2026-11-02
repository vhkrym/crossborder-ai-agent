"""HTTP-level deterministic business chain, isolated DB; never calls a provider."""
import json,hashlib
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from app.db.session import build_engine,get_db
from app.demo.seed import seed_demo
from app.db.migrate_agent_tasks import migrate as mt
from app.db.migrate_decisions import migrate as md
from app.db.migrate_decision_approvals import migrate as ma
from app.db.migrate_decision_simulations import migrate as ms
from app.services.agent_tasks import AgentTaskService
from app.services.decisions import DecisionService
from app.services.decision_approvals import ApprovalService
from app.services.simulations import SimulationService
from app.api.v1.router import router
from app.api.v1.agent_tasks import get_task_service
from app.api.v1.decisions import get_decision_service
from app.api.v1.decision_approvals import get_approval_service
from app.api.v1.simulations import get_simulation_service
from app.agents.supervisor_graph import build_supervisor_graph
from test_supervisor import FakeLLM

class All(FakeLLM):
    def invoke(self,messages):
        r=super().invoke(messages)
        if 'evidence' not in json.loads(messages[-1].content):r.content=json.dumps(dict(intent='mixed',selected_agents=['profit','advertising','inventory'],reason='quality audit'))
        return r

def business_hashes(e):
    with e.connect() as c:
        return {t:hashlib.sha256(json.dumps(c.execute(text('SELECT * FROM '+t+' ORDER BY id')).fetchall(),default=str).encode()).hexdigest() for t in ['stores','products','sales_records','ad_records','inventory_snapshots','cost_records','data_imports']}

def test_full_http_chain(tmp_path):
    e=build_engine('sqlite:///'+(tmp_path/'chain.db').as_posix());seed_demo(e)
    for _ in range(2):
        for migrate in (mt,md,ma,ms):migrate(e)
    f=sessionmaker(bind=e);before=business_hashes(e)
    tasksvc=AgentTaskService(f,lambda state,factory:build_supervisor_graph(All('mixed'),factory).invoke(state.model_dump()))
    simsvc=SimulationService(f)
    app=FastAPI();app.include_router(router,prefix='/api/v1')
    app.dependency_overrides[get_task_service]=lambda:tasksvc
    app.dependency_overrides[get_decision_service]=lambda:DecisionService(f)
    app.dependency_overrides[get_approval_service]=lambda:ApprovalService(f)
    app.dependency_overrides[get_simulation_service]=lambda:simsvc
    with TestClient(app) as c:
        root='/api/v1'
        r=c.post(root+'/agent/tasks',json=dict(store_id=1,user_query='分析三维风险',start_date='2026-01-01',end_date='2026-03-31',selected_sku='DEMO-001'))
        assert r.status_code==202;tid=r.json()['task_id']
        task=c.get(root+'/agent/tasks/'+tid).json()
        assert task['status']=='completed' and set(task['selected_agents'])=={'profit','advertising','inventory'}
        assert len(task['trace_json']['tools'])==3
        decisions=c.post(root+'/decisions/generate',json={'source_task_id':tid});assert decisions.status_code==200,decisions.text
        proposals=decisions.json()['proposals'];assert proposals and all(p['sku']=='DEMO-001' and p['store_id']==1 and p['source_task_id']==tid for p in proposals)
        p=next(p for p in proposals if p['proposal_type']=='profit_review');pid=p['proposal_id']
        assert p['evidence_json']['metrics']['contribution_profit']=='-10286.6500'
        again=c.post(root+'/decisions/generate',json={'source_task_id':tid}).json();assert again['reused'] and len(again['proposals'])==len(proposals)
        assert c.post(root+f'/decisions/{pid}/simulate',json={}).status_code==409
        approved=c.post(root+f'/decisions/{pid}/approve',params={'store_id':1},json={'comment':'本地链路回归审核'});assert approved.status_code==200
        aid=approved.json()['audit']['audit_id']
        sim=c.post(root+f'/decisions/{pid}/simulate',json={});assert sim.status_code==200
        sid=sim.json()['simulation_id'];assert sim.json()['status']=='simulation_completed'
        assert c.post(root+f'/decisions/{pid}/simulate',json={}).json()['reused']
        detail=c.get(root+'/simulations/'+sid).json()
        assert detail['approval_audit_id']==aid and detail['source_task_id']==tid
        assert detail['output_json']['simulation_only'] is True and detail['input_snapshot_json']['proposal']['status']=='approved'
        assert c.get(root+f'/decisions/{pid}/audit',params={'store_id':1}).json()[0]['audit_id']==aid
        assert c.get(root+'/simulations',params={'store_id':1}).json()['total']==1
        assert c.get(root+'/simulations',params={'store_id':2}).json()['total']==0
        assert c.post(root+f'/decisions/{pid}/approve',params={'store_id':1},json={}).status_code==409
        assert tasksvc.recover()==0 and simsvc.recover()==0
    for migrate in (mt,md,ma,ms):migrate(e)
    assert business_hashes(e)==before
    with e.connect() as c:
        assert c.scalar(text('PRAGMA foreign_keys'))==1 and c.exec_driver_sql('PRAGMA foreign_key_check').fetchall()==[]
    e.dispose()
