from decimal import Decimal
from app.models import AdRecord, Store
from app.analytics.common import ZERO, ratio, skus, facts

def analyze_advertising(session,store_id,start,end,sku=None):
    if start>end: raise ValueError('start_date must not exceed end_date')
    result=[]
    for code in skus(session,store_id,sku):
        rows=facts(session,AdRecord,store_id,start,end,code)
        spend=sum((r.spend for r in rows),ZERO); attributed=sum((r.attributed_sales for r in rows),ZERO)
        clicks=sum(r.clicks for r in rows); orders=sum(r.orders for r in rows)
        reasons=[]
        if not rows: reasons.append('no_ad_records')
        if not spend: reasons.append('zero_spend')
        if not attributed: reasons.append('zero_attributed_sales')
        if not clicks: reasons.append('zero_clicks')
        mismatch=any(r.currency!=session.get(Store,store_id).currency for r in rows)
        if mismatch: reasons.append('currency_mismatch')
        result.append(dict(sku=code,spend=spend,attributed_sales=attributed,clicks=clicks,ad_orders=orders,acos=None if mismatch else ratio(spend,attributed),roas=None if mismatch else ratio(attributed,spend),cpc=None if mismatch else ratio(spend,clicks),conversion_rate=ratio(Decimal(orders),clicks),reasons=reasons))
    return result
