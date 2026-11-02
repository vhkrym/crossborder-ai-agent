from datetime import date
from decimal import Decimal
import pytest
from pydantic import ValidationError
from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker
from app.db.session import build_engine
from app.db.init_db import init_db
from app.demo.seed import seed_demo
from app.models import Store
from app.agents.state import AgentState
from app.agents.graph import build_graph
from app.tools.analytics_tools import AnalysisInput, build_tools, execute_analysis

PARAMS=dict(store_id=1,start_date='2026-01-01',end_date='2026-03-31')
@pytest.fixture(scope='module')
def factory(tmp_path_factory):
    e=build_engine('sqlite:///'+(tmp_path_factory.mktemp('agent')/'test.db').as_posix());seed_demo(e)
    yield sessionmaker(bind=e)
    e.dispose()

def test_state():
    s=AgentState(**PARAMS,task_id='task-1',user_query='分析',selected_tools=['analyze_profit'])
    assert s.execution_status=='pending' and s.final_answer is None and not s.tool_results
    assert AgentState.model_validate_json(s.model_dump_json())==s

@pytest.mark.parametrize('change',[dict(store_id=0),dict(start_date='2027-01-01'),dict(selected_sku=' '),dict(window=0),dict(safety_days=-1),dict(selected_sku='x'*101)])
def test_input_validation(change):
    with pytest.raises(ValidationError): AnalysisInput(**(PARAMS|change))

def test_tools_and_demo(factory):
    tools=build_tools(factory)
    for name,sku,key in [('analyze_profit','DEMO-001','profit'),('analyze_advertising','DEMO-002','advertising'),('analyze_inventory','DEMO-003','inventory')]:
        result=tools[name].invoke(PARAMS|dict(selected_sku=sku))
        assert result['status']=='warning' and result['parameters']['store_id']==1
        assert result['data']['currency']=='USD' and result['conventions']
        row=result['data'][key][0]
        if key=='profit': assert Decimal(row['contribution_profit'])<0
        if key=='advertising': assert Decimal(row['acos'])>1
        if key=='inventory': assert row['risk']=='stockout' and row['suggested_replenishment'] is None
        isolated=tools[name].invoke(PARAMS|dict(store_id=2,selected_sku=sku))
        assert isolated['status']=='failed' and isolated['error']=='store_or_sku_not_found'
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(Store))==2
        assert s.connection().exec_driver_sql('PRAGMA query_only').scalar()==0

def test_graph(factory):
    state=AgentState(**PARAMS,task_id='workflow',user_query='analysis',selected_tools=['analyze_profit','analyze_advertising','analyze_inventory'])
    result=AgentState.model_validate(build_graph(factory).invoke(state.model_dump()))
    assert result.execution_status=='completed' and len(result.tool_results)==3 and len(result.traces)==4
    assert not result.errors and result.final_answer
    assert [t.node for t in result.traces]==['execute_tools']*3+['summarize']
    assert all(t.ended_at>=t.started_at and t.summary for t in result.traces)
    assert 'password' not in result.model_dump_json()

def test_failure_and_missing(factory,tmp_path):
    bad=AgentState(**(PARAMS|dict(store_id=999)),task_id='bad',user_query='query',selected_tools=['analyze_profit'])
    result=AgentState.model_validate(build_graph(factory).invoke(bad.model_dump()))
    assert result.execution_status=='failed' and result.errors and result.traces[0].error
    assert result.tool_results['analyze_profit'].data is None
    empty=build_engine('sqlite:///'+(tmp_path/'empty.db').as_posix())
    failed=execute_analysis('analyze_profit',AnalysisInput(**PARAMS),sessionmaker(bind=empty))
    assert failed.status=='failed' and failed.error=='database_error'
    empty.dispose()
    missing=execute_analysis('analyze_profit',AnalysisInput(**(PARAMS|dict(start_date='2025-01-01',end_date='2025-01-31',selected_sku='DEMO-001'))),factory)
    assert missing.status=='warning' and missing.data.profit[0].contribution_profit is None

def test_unknown_tool_and_state_fields():
    with pytest.raises(ValidationError): AgentState(**PARAMS,task_id='x',user_query='query',selected_tools=['not_a_tool'])
    with pytest.raises(ValidationError): AgentState(**PARAMS,task_id='',user_query='query',selected_tools=[])


def test_same_sku_isolation_and_unexpected_failure(tmp_path):
    from app.models import Product, SalesRecord
    from app.agents.nodes import execute_tools, summarize
    e=build_engine('sqlite:///'+(tmp_path/'isolated.db').as_posix());init_db(e);sessions=sessionmaker(bind=e)
    with sessions() as s:
        s.add_all([Store(id=i,name=str(i),marketplace='Amazon',market='US',currency='USD') for i in (1,2)]);s.flush()
        s.add_all([Product(store_id=i,sku='SAME') for i in (1,2)]);s.flush()
        for i in (1,2):s.add(SalesRecord(store_id=i,sku='SAME',record_date=date(2026,1,1),quantity=i,gross_sales=i*10,refund_amount=0,currency='USD'))
        s.commit()
    for i in (1,2):
        r=execute_analysis('analyze_profit',AnalysisInput(**(PARAMS|dict(store_id=i,selected_sku='SAME'))),sessions)
        assert r.data.profit[0].net_revenue==i*10 and r.status=='warning'
    class Broken:
        def invoke(self,params):raise RuntimeError('password=SECRET')
    state=AgentState(**PARAMS,task_id='failure',user_query='query',selected_tools=['analyze_profit'])
    updates=execute_tools(state,{'analyze_profit':Broken()})
    result=state.model_copy(update=updates)
    assert summarize(result)['execution_status']=='failed'
    assert 'SECRET' not in result.model_dump_json()
    e.dispose()
