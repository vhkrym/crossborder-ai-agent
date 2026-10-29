from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import inspect, text, select, Numeric, Table, Column, MetaData
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db.session import build_engine
from app.db.init_db import init_db
from app.core.money import normalize_money
from app.models import CostRecord, SalesRecord
from app.services.costs import get_applicable_cost

@pytest.fixture
def engine(tmp_path):
    e = build_engine('sqlite:///' + (tmp_path / 'test.db').as_posix())
    init_db(e)
    with e.begin() as c:
        c.execute(text("INSERT INTO stores VALUES (1,'one','Amazon','US','USD'),(2,'two','Amazon','US','USD')"))
        c.execute(text("INSERT INTO products VALUES (1,1,'A'),(2,2,'A')"))
    yield e
    e.dispose()

def test_tables_engine_and_idempotent_init(engine):
    assert set(inspect(engine).get_table_names()) == {'stores','products','sales_records','ad_records','inventory_snapshots','cost_records','data_imports'}
    for _ in range(2):
        with engine.connect() as c: assert c.scalar(text('PRAGMA foreign_keys')) == 1
        engine.dispose()
    init_db(engine)
    with engine.connect() as c: assert c.scalar(text('SELECT COUNT(*) FROM products')) == 2

@pytest.mark.parametrize('sql', [
    "INSERT INTO products VALUES (3,1,'A')",
    "INSERT INTO products VALUES (3,99,'A')",
    "INSERT INTO stores VALUES (3,NULL,'x','US','USD')",
    "INSERT INTO products VALUES (3,1,NULL)",
    "INSERT INTO sales_records (id,store_id,sku,record_date,quantity,gross_sales,refund_amount,currency) VALUES (1,1,'B','2026-01-01',1,1,0,'USD')",
    "INSERT INTO sales_records (id,store_id,sku,record_date,quantity,gross_sales,refund_amount,currency) VALUES (1,1,'A',NULL,1,1,0,'USD')",
    "INSERT INTO sales_records (id,store_id,sku,record_date,quantity,gross_sales,refund_amount,currency) VALUES (1,1,'A','2026-01-01',1,-1,0,'USD')",
    "INSERT INTO ad_records (id,store_id,sku,record_date,spend,attributed_sales,clicks,orders,currency) VALUES (1,1,'A','2026-01-01',1,1,-1,0,'USD')",
    "INSERT INTO inventory_snapshots (id,store_id,sku,snapshot_date,on_hand,reserved,inbound,lead_time_days) VALUES (1,1,'A','2026-01-01',1,2,0,1)",
    "INSERT INTO inventory_snapshots (id,store_id,sku,snapshot_date,on_hand,reserved,inbound,lead_time_days) VALUES (1,1,'A','2026-01-01',1,0,-1,1)",
    "INSERT INTO cost_records (id,store_id,sku,effective_from,purchase_cost,logistics_cost,platform_fee_per_unit,currency) VALUES (1,1,'A','2026-01-01',-1,0,0,'USD')",
])
def test_database_rejects_invalid(engine, sql):
    with pytest.raises(IntegrityError):
        with engine.begin() as c: c.execute(text(sql))

@pytest.mark.parametrize('table', ['stores','products'])
def test_no_cascade_history(engine, table):
    with engine.begin() as c:
        c.execute(text("INSERT INTO sales_records (id,store_id,sku,record_date,quantity,gross_sales,refund_amount,currency) VALUES (1,1,'A','2026-01-01',1,1,0,'USD')"))
    with pytest.raises(IntegrityError):
        with engine.begin() as c: c.execute(text(f'DELETE FROM {table} WHERE id=1'))
    with engine.connect() as c: assert c.scalar(text('SELECT COUNT(*) FROM sales_records')) == 1

def test_cost_boundaries_and_money(engine):
    with Session(engine) as s:
        for month in (1,3):
            s.add(CostRecord(store_id=1,sku='A',effective_from=date(2026,month,1),purchase_cost=Decimal('999999.9999'),logistics_cost='0.10005',platform_fee_per_unit=0,currency='USD'))
        s.commit()
        assert get_applicable_cost(s,1,'A',date(2025,12,31)) is None
        for business_date, expected in [(date(2026,1,1),1),(date(2026,2,28),1),(date(2026,3,1),3),(date(2026,12,1),3)]:
            row=get_applicable_cost(s,1,'A',business_date)
            assert row.effective_from.month == expected
            assert row.purchase_cost == Decimal('999999.9999')
            assert row.logistics_cost == Decimal('0.1001')
        for _ in range(2):
            s.add(SalesRecord(store_id=1,sku='A',record_date=date(2026,1,1),quantity=1,gross_sales='12.3456',refund_amount=0,currency='USD'))
        s.commit()
        rows=s.scalars(select(SalesRecord)).all()
        assert len(rows)==2 and all(r.gross_sales == Decimal('12.3456') for r in rows)

@pytest.mark.parametrize('value', [0.1, True, '-1', 'NaN', 'Infinity', '1000000'])
def test_money_rejects(value):
    with pytest.raises(ValueError): normalize_money(value)

def test_sqlite_numeric_limitation(engine):
    t=Table('precision_probe',MetaData(),Column('amount',Numeric(18,4)))
    t.create(engine)
    original=Decimal('99999999999999.9999')
    with engine.begin() as c:
        c.execute(t.insert().values(amount=original))
        assert c.scalar(select(t.c.amount)) != original

def test_import_identity_and_retry(engine):
    sql=text("INSERT INTO data_imports (store_id,source_type,file_hash,filename,data_type,status,total_rows,success_rows,failed_rows,created_at) VALUES (:store,'file',:hash,'a.csv','sales_records',:status,0,0,0,CURRENT_TIMESTAMP)")
    identity=dict(store=1,hash='a'*64,status='failed')
    with engine.begin() as c: c.execute(sql,identity)
    with pytest.raises(IntegrityError):
        with engine.begin() as c: c.execute(sql,identity)
    with engine.begin() as c:
        c.execute(text("UPDATE data_imports SET status='pending',error_summary=NULL WHERE store_id=1"))
        c.execute(sql,dict(identity,store=2,status='completed'))
    with pytest.raises(IntegrityError):
        with engine.begin() as c: c.execute(sql,dict(identity,hash='invalid'))
