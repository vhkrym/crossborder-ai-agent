from datetime import date, timedelta
from decimal import Decimal as D
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.db.session import build_engine, get_db
from app.db.init_db import init_db
from app.models import Store, Product, SalesRecord, AdRecord, CostRecord, InventorySnapshot
from app.analytics.profit import analyze_profit
from app.analytics.advertising import analyze_advertising
from app.analytics.inventory import analyze_inventory
from app.main import create_app

START=date(2026,1,1)
@pytest.fixture
def db(tmp_path):
    e=build_engine('sqlite:///'+(tmp_path/'analysis.db').as_posix()); init_db(e)
    with Session(e) as s:
        for i in (1,2): s.add(Store(id=i,name=str(i),marketplace='Amazon',market='US',currency='USD'))
        s.flush()
        for i in (1,2): s.add(Product(store_id=i,sku='A'))
        s.flush()
        for day,cost in [(0,2),(1,3)]: s.add(CostRecord(store_id=1,sku='A',effective_from=START+timedelta(days=day),purchase_cost=cost,logistics_cost=1,platform_fee_per_unit=1,currency='USD'))
        for day in (0,1):
            for _ in range(2):
                s.add(SalesRecord(store_id=1,sku='A',record_date=START+timedelta(days=day),quantity=2,gross_sales=20,refund_amount=1,currency='USD'))
                s.add(AdRecord(store_id=1,sku='A',record_date=START+timedelta(days=day),spend=2,attributed_sales=10,clicks=4,orders=1,currency='USD'))
        s.add(InventorySnapshot(store_id=1,sku='A',snapshot_date=START+timedelta(days=1),on_hand=10,reserved=2,inbound=100,lead_time_days=3))
        s.commit(); yield s
    e.dispose()

def test_hand_calculation(db):
    end=START+timedelta(days=1)
    r=analyze_profit(db,1,START,end)[0]
    assert r['net_revenue']==76 and r['purchase_cost']==20 and r['logistics_cost']==8 and r['platform_fees']==8 and r['ad_spend']==8
    assert r['contribution_profit']==32 and r['profit_margin']==D(32)/76 and r['cost_increased']
    a=analyze_advertising(db,1,START,end)[0]
    assert (a['acos'],a['roas'],a['cpc'],a['conversion_rate'])==(D('0.2'),D(5),D('0.5'),D('0.25'))
    i=analyze_inventory(db,1,end,window=2,safety_days=1)[0]
    assert i['average_daily_sales']==4 and i['coverage_days']==2 and i['suggested_replenishment']==8 and i['risk']=='at_risk'
    assert analyze_profit(db,1,START,START)[0]['purchase_cost']==8
    assert analyze_profit(db,2,START,end)[0]['contribution_profit'] is None
    assert analyze_inventory(db,2,end,window=2)[0]['risk']=='unknown'
    assert 'insufficient_history' in analyze_inventory(db,1,end,window=30)[0]['reasons']

def test_future_zero_negative_missing(db):
    future=START+timedelta(days=10)
    db.add(SalesRecord(store_id=2,sku='A',record_date=START,quantity=1,gross_sales=0,refund_amount=5,currency='USD'))
    db.add(SalesRecord(store_id=1,sku='A',record_date=future,quantity=100,gross_sales=1000,refund_amount=0,currency='USD'))
    db.add(InventorySnapshot(store_id=1,sku='A',snapshot_date=future,on_hand=999,reserved=0,inbound=0,lead_time_days=1))
    db.commit()
    r=analyze_profit(db,2,START,START)[0]
    assert r['net_revenue']==-5 and r['profit_margin'] is None and 'missing_cost' in r['reasons']
    a=analyze_advertising(db,2,START,START)[0]
    assert a['acos'] is None and a['roas'] is None and a['cpc'] is None
    assert analyze_profit(db,1,START,START)[0]['quantity']==4
    assert analyze_inventory(db,1,START)[0]['snapshot_date'] is None
    i=analyze_inventory(db,1,START+timedelta(days=2),window=1)[0]
    assert 'stale_snapshot' in i['reasons'] and i['risk']=='unknown'
    db.add(SalesRecord(store_id=2,sku='A',record_date=START+timedelta(days=1),quantity=0,gross_sales=0,refund_amount=0,currency='USD'))
    db.add(InventorySnapshot(store_id=2,sku='A',snapshot_date=START+timedelta(days=1),on_hand=50,reserved=0,inbound=0,lead_time_days=2)); db.commit()
    i=analyze_inventory(db,2,START+timedelta(days=1),window=1)[0]
    assert i['risk']=='zero_sales_stock' and i['coverage_days'] is None

@pytest.mark.parametrize('path',['dashboard/overview','analytics/profit','analytics/advertising','analytics/inventory-risk'])
def test_api(db,path):
    app=create_app(); app.dependency_overrides[get_db]=lambda: db
    with TestClient(app) as c:
        params=dict(store_id=1,start_date='2026-01-01',end_date='2026-01-02')
        r=c.get('/api/v1/'+path,params=params)
        assert r.status_code==200,r.text
        body=r.json(); assert body['currency']=='USD' and body['store_id']==1 and 'units' in body
        assert c.get('/api/v1/'+path,params={**params,'window':0}).status_code==422
        assert c.get('/api/v1/'+path,params={**params,'start_date':'2027-01-01'}).status_code==422
        assert c.get('/api/v1/'+path,params={**params,'store_id':99}).status_code==404
        assert c.get('/api/v1/'+path,params={**params,'sku':'missing'}).status_code==404
        assert c.get('/api/v1/'+path,params={**params,'store_id':0}).status_code==422

def test_demo_scenarios(tmp_path):
    from app.demo.seed import seed_demo
    e=build_engine('sqlite:///'+(tmp_path/'demo.db').as_posix()); seed_demo(e)
    with Session(e) as s:
        end=date(2026,3,31)
        profits={r['sku']:r for r in analyze_profit(s,1,START,end)}
        ads={r['sku']:r for r in analyze_advertising(s,1,START,end)}
        inv={r['sku']:r for r in analyze_inventory(s,1,end)}
        assert profits['DEMO-001']['quantity']>3000 and profits['DEMO-001']['profit_margin']<D('.05')
        assert profits['DEMO-005']['cost_increased']
        before=analyze_profit(s,1,START,date(2026,1,30),'DEMO-005')[0]
        after=analyze_profit(s,1,date(2026,2,15),end,'DEMO-005')[0]
        assert after['profit_margin']<before['profit_margin']
        assert ads['DEMO-002']['acos']>1
        assert inv['DEMO-003']['risk']=='stockout' and inv['DEMO-003']['suggested_replenishment'] is None
        assert inv['DEMO-004']['coverage_days']>365 and inv['DEMO-004']['risk']=='slow_moving_stock'
        print('DEMO_RESULTS',profits['DEMO-001'],ads['DEMO-002'],inv['DEMO-003'],inv['DEMO-004'],before['profit_margin'],after['profit_margin'])
    e.dispose()


def test_overview_summary(db):
    from app.services.analytics import analyze
    r=analyze(db,'overview',1,START,START+timedelta(days=1),window=2)
    assert r.summary.net_revenue==76
    assert r.summary.contribution_profit==32
    assert r.summary.acos==D('0.2')
    assert r.summary.inventory_risk_skus==1
    empty=analyze(db,'overview',2,START,START)
    assert empty.summary.contribution_profit is None
    assert empty.summary.inventory_unknown_skus==1
