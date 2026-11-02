from decimal import Decimal
from sqlalchemy import select
from app.models import Product

ZERO = Decimal(0)
def ratio(a,b):
    return a/b if b>0 else None

def skus(session,store_id,sku=None):
    q=select(Product.sku).where(Product.store_id==store_id)
    if sku: q=q.where(Product.sku==sku)
    return list(session.scalars(q.order_by(Product.sku)))

def facts(session,model,store_id,start,end,sku):
    return list(session.scalars(select(model).where(model.store_id==store_id,model.sku==sku,model.record_date>=start,model.record_date<=end)))
