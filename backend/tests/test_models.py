from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine, event, select, func
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session
from app.db.init_db import init_db
from app.models import Store, Product, SalesRecord, AdRecord, InventorySnapshot, CostRecord, DataImport
from app.services.costs import get_applicable_cost

@pytest.fixture
def db():
    engine = create_engine('sqlite:///:memory:')
    event.listen(engine, 'connect', lambda connection, _: connection.execute('PRAGMA foreign_keys=ON'))
    init_db(engine)
    with Session(engine) as session:
        session.add_all([Store(id=i, name=str(i), marketplace='Amazon', market='US', currency='USD') for i in (1, 2)])
        session.commit()
        session.add(Product(store_id=1, sku='A'))
        session.commit()
        yield session
    engine.dispose()

def test_product_scope_and_initialization(db):
    db.add(Product(store_id=2, sku='A'))
    db.commit()
    init_db(db.get_bind())
    assert db.scalar(select(func.count()).select_from(Product)) == 2
    db.add(Product(store_id=1, sku='A'))
    with pytest.raises((IntegrityError, StatementError)): db.commit()

@pytest.mark.parametrize('model,values', [
    (Product, dict(store_id=99, sku='A')),
    (SalesRecord, dict(store_id=2, sku='A', record_date=date.today(), quantity=1, gross_sales=1, refund_amount=0, currency='USD')),
    (SalesRecord, dict(store_id=1, sku='A', record_date=date.today(), quantity=-1, gross_sales=1, refund_amount=0, currency='USD')),
    (AdRecord, dict(store_id=1, sku='A', record_date=date.today(), spend=-1, attributed_sales=0, clicks=0, orders=0, currency='USD')),
    (InventorySnapshot, dict(store_id=1, sku='A', snapshot_date=date.today(), on_hand=1, reserved=2, inbound=0, lead_time_days=1)),
    (CostRecord, dict(store_id=1, sku='A', effective_from=date.today(), purchase_cost=-1, logistics_cost=0, platform_fee_per_unit=0, currency='USD')),
    (DataImport, dict(store_id=1, file_hash='a'*64, filename='x.csv', data_type='products', status='invalid')),
    (DataImport, dict(store_id=1, file_hash='a'*64, filename='x.csv', data_type='products', total_rows=1, success_rows=2)),
])
def test_invalid_data(db, model, values):
    db.add(model(**values))
    with pytest.raises((IntegrityError, StatementError)): db.commit()


def test_cost_precision_and_date(db):
    for month in (1, 3):
        db.add(CostRecord(store_id=1, sku='A', effective_from=date(2026, month, 1), purchase_cost=Decimal('12.3456'), logistics_cost=Decimal('0.1000'), platform_fee_per_unit=Decimal('0.2000'), currency='USD'))
    db.commit()
    assert get_applicable_cost(db, 1, 'A', date(2025, 1, 1)) is None
    cost = get_applicable_cost(db, 1, 'A', date(2026, 2, 1))
    assert cost.effective_from == date(2026, 1, 1)
    assert cost.purchase_cost == Decimal('12.3456')
    assert cost.logistics_cost + cost.platform_fee_per_unit == Decimal('0.3000')
    db.add(CostRecord(store_id=1, sku='A', effective_from=cost.effective_from, purchase_cost=0, logistics_cost=0, platform_fee_per_unit=0, currency='USD'))
    with pytest.raises((IntegrityError, StatementError)): db.commit()


def test_inventory_unique_date(db):
    values = dict(store_id=1, sku='A', snapshot_date=date.today(), on_hand=5, reserved=2, inbound=1, lead_time_days=3)
    row = InventorySnapshot(**values)
    assert row.available == 3
    db.add(row)
    db.commit()
    db.add(InventorySnapshot(**values))
    with pytest.raises((IntegrityError, StatementError)): db.commit()
