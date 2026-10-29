from datetime import timedelta
from decimal import Decimal
import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.db.session import build_engine
from app.demo.seed import seed_demo
from app.demo.generator import generate, DEFAULT_START
from app.models import Store, SalesRecord, InventorySnapshot, CostRecord, DataImport
from app.services.costs import get_applicable_cost

@pytest.fixture
def demo(tmp_path):
    e=build_engine('sqlite:///'+(tmp_path/'test.demo.db').as_posix())
    counts=seed_demo(e)
    yield e,counts
    e.dispose()

def test_counts_idempotency_and_relations(demo):
    e,counts=demo
    assert counts==dict(stores=2,products=30,sales_records=2700,ad_records=2700,inventory_snapshots=2700,cost_records=33,data_imports=12)
    assert seed_demo(e)==counts
    with e.connect() as c:
        assert not c.execute(text('PRAGMA foreign_key_check')).all()
        assert c.scalar(text('SELECT COUNT(*) FROM sales_records'))==2700
    with Session(e) as s:
        dates=set(s.scalars(select(SalesRecord.record_date)))
        assert dates=={DEFAULT_START+timedelta(days=i) for i in range(90)}
        for row in s.scalars(select(DataImport)):
            assert row.filename.startswith('demo-seed/') and len(row.file_hash)==64
            assert row.total_rows==row.success_rows and row.failed_rows==0
        for row in s.scalars(select(SalesRecord)):
            assert isinstance(row.gross_sales,Decimal) and row.gross_sales>=0 and row.refund_amount>=0
            assert row.gross_sales.as_tuple().exponent==-4
    with pytest.raises(ValueError): seed_demo(e,seed=43)

def test_reproducible():
    assert generate()==generate()
    assert generate()!=generate(seed=43)

def test_inventory_conservation(demo):
    e,_=demo
    with Session(e) as s:
        for number in range(1,31):
            sku=f'DEMO-{number:03d}'
            sales=s.scalars(select(SalesRecord).where(SalesRecord.sku==sku).order_by(SalesRecord.record_date)).all()
            snaps=s.scalars(select(InventorySnapshot).where(InventorySnapshot.sku==sku).order_by(InventorySnapshot.snapshot_date)).all()
            for i,snap in enumerate(snaps):
                assert 0<=snap.reserved<=snap.on_hand and snap.inbound>=0
                if i:
                    received=snap.on_hand-snaps[i-1].on_hand+sales[i].quantity
                    ordered=snap.inbound-snaps[i-1].inbound+received
                    assert received>=0 and ordered>=0
                    if received: assert received==snaps[i-1].inbound

def test_five_scenarios(demo):
    e,_=demo
    with Session(e) as s:
        rows=s.scalars(select(SalesRecord).where(SalesRecord.sku=='DEMO-001')).all()
        revenue=sum(r.gross_sales-r.refund_amount for r in rows)
        units=sum(r.quantity for r in rows)
        assert units>3000 and (revenue-Decimal('20')*units)/revenue<Decimal('0.05')
        from app.models import AdRecord
        ads=s.scalars(select(AdRecord).where(AdRecord.sku=='DEMO-002')).all()
        assert sum(r.spend for r in ads)/sum(r.attributed_sales for r in ads)>1
        latest=s.scalar(select(InventorySnapshot).where(InventorySnapshot.sku=='DEMO-003').order_by(InventorySnapshot.snapshot_date.desc()))
        assert latest.available==0 and latest.inbound>0
        rows=s.scalars(select(SalesRecord).where(SalesRecord.sku=='DEMO-003')).all()
        assert any(r.refund_amount>r.gross_sales for r in rows)
        slow=s.scalars(select(SalesRecord).where(SalesRecord.sku=='DEMO-004')).all()
        latest=s.scalar(select(InventorySnapshot).where(InventorySnapshot.sku=='DEMO-004').order_by(InventorySnapshot.snapshot_date.desc()))
        assert sum(r.quantity for r in slow)<=5 and latest.on_hand>=790
        before=get_applicable_cost(s,1,'DEMO-005',DEFAULT_START+timedelta(days=44))
        after=get_applicable_cost(s,1,'DEMO-005',DEFAULT_START+timedelta(days=45))
        assert after.purchase_cost-before.purchase_cost==Decimal('7')
        price=Decimal('32')
        assert (price-after.purchase_cost-after.logistics_cost-after.platform_fee_per_unit)/price < (price-before.purchase_cost-before.logistics_cost-before.platform_fee_per_unit)/price

def test_refuses_existing_business(tmp_path):
    from app.db.init_db import init_db
    e=build_engine('sqlite:///'+(tmp_path/'business.db').as_posix())
    init_db(e)
    with Session(e) as s:
        s.add(Store(name='real',marketplace='Amazon',market='US',currency='USD')); s.commit()
    with pytest.raises(ValueError): seed_demo(e)
    with Session(e) as s: assert s.scalar(select(Store.name))=='real'
    e.dispose()
