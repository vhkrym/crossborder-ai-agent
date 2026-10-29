"""Dedicated demo databases only; no reset/delete capability."""
import hashlib
import json
from decimal import Decimal
from datetime import datetime, time
from sqlalchemy import inspect, select, func
from sqlalchemy.orm import Session
from app.db.init_db import init_db
from app.models import Store, Product, SalesRecord, AdRecord, InventorySnapshot, CostRecord, DataImport
from app.demo.generator import generate, DEFAULT_START

MODELS = dict(zip(('stores','products','sales_records','ad_records','inventory_snapshots','cost_records'), (Store,Product,SalesRecord,AdRecord,InventorySnapshot,CostRecord)))

def canonical(value):
    return json.dumps(value,default=lambda v: format(v.normalize(), "f") if isinstance(v, Decimal) else str(v),sort_keys=True,separators=(',',':')).encode()

def seed_demo(engine, seed=42, start=DEFAULT_START, days=90):
    if not 14 <= days <= 366:
        raise ValueError('days must be between 14 and 366')
    data = generate(seed,start,days)
    fingerprint = hashlib.sha256(json.dumps(data,default=str,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    # Refuse any populated database unless its complete contents match this demo.
    tables = inspect(engine).get_table_names()
    if tables:
        with engine.connect() as c:
            populated = any(c.scalar(select(func.count()).select_from(model)) for model in MODELS.values())
        if populated:
            with Session(engine) as s:
                for name,model in MODELS.items():
                    actual=[{column.name:getattr(row,column.name) for column in model.__table__.columns if column.name in data[name][0]} for row in s.scalars(select(model).order_by(model.id))]
                    if canonical(actual) != canonical(data[name]):
                        raise ValueError('database is populated or demo configuration differs; choose a new demo database')
                imports=s.scalars(select(DataImport)).all()
                if len(imports)!=12 or any(row.status!='completed' or row.filename!=f'demo-seed/{fingerprint}/{row.data_type}.json' for row in imports):
                    raise ValueError('demo import manifest mismatch')
            return {**{k:len(v) for k,v in data.items()},'data_imports':12}
    init_db(engine)
    with Session(engine) as s, s.begin():
        for name,model in MODELS.items():
            s.add_all(model(**row) for row in data[name]); s.flush()
        for store in (1,2):
            for name,rows in data.items():
                payload=[row for row in rows if row.get('store_id',row.get('id'))==store]
                s.add(DataImport(store_id=store,source_type='file',filename=f'demo-seed/{fingerprint}/{name}.json',file_hash=hashlib.sha256(canonical(payload)).hexdigest(),data_type=name,status='completed',total_rows=len(payload),success_rows=len(payload),failed_rows=0,created_at=datetime.combine(start,time())))
    return {**{k:len(v) for k,v in data.items()},'data_imports':12}
