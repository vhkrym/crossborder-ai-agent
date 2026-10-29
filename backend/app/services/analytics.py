from datetime import timedelta
from decimal import Decimal
from app.models import Store, Product
from app.analytics.profit import analyze_profit
from app.analytics.advertising import analyze_advertising
from app.analytics.inventory import analyze_inventory
from app.schemas.analytics import AnalysisResponse
from sqlalchemy import select

class AnalyticsNotFound(ValueError): pass

def analyze(session,kind,store_id,start,end,sku=None,window=30,safety_days=7,sort_by='contribution_profit',descending=True):
    if start>end: raise ValueError('start_date must not exceed end_date')
    store=session.get(Store,store_id)
    if not store: raise AnalyticsNotFound('store not found')
    if sku and not session.scalar(select(Product.id).where(Product.store_id==store_id,Product.sku==sku)):
        raise AnalyticsNotFound('SKU not found in store')
    result=AnalysisResponse(store_id=store_id,currency=store.currency,start_date=start,end_date=end)
    if kind in ('profit','overview'):
        result.profit=analyze_profit(session,store_id,start,end,sku,sort_by,descending)
    if kind in ('advertising','overview'):
        result.advertising=analyze_advertising(session,store_id,start,end,sku)
    if kind in ('inventory','overview'):
        result.inventory=analyze_inventory(session,store_id,end,sku,window,safety_days)
        result.window=window; result.safety_days=safety_days
        if kind=='inventory': result.start_date=end-timedelta(days=window-1)
    if not (result.profit or result.advertising or result.inventory): result.reasons=['no_products']
    if kind=='overview':
        zero=Decimal(0)
        reasons=[]
        currency_invalid=any('currency_mismatch' in r.reasons for r in result.profit+result.advertising)
        revenue=sum((r.net_revenue for r in result.profit),zero) if result.profit and not currency_invalid else None
        profit=sum((r.contribution_profit for r in result.profit),zero) if result.profit and all(r.contribution_profit is not None for r in result.profit) else None
        attributed=sum((r.attributed_sales for r in result.advertising),zero)
        spend=sum((r.spend for r in result.advertising),zero)
        if revenue is None: reasons.append('revenue_unavailable')
        if profit is None: reasons.append('profit_incomplete')
        if currency_invalid: reasons.append('currency_mismatch')
        if not attributed: reasons.append('zero_attributed_sales')
        result.summary=dict(net_revenue=revenue,contribution_profit=profit,acos=spend/attributed if attributed>0 and not currency_invalid else None,inventory_risk_skus=sum(r.risk in ('stockout','at_risk') for r in result.inventory),inventory_unknown_skus=sum(r.risk=='unknown' for r in result.inventory),reasons=reasons)
    # Revalidate nested dictionaries before serialization.
    return AnalysisResponse.model_validate(result.model_dump())
