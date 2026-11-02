from sqlalchemy import select
from app.models import SalesRecord, AdRecord, CostRecord
from app.analytics.common import ZERO, ratio, skus, facts

def analyze_profit(session,store_id,start,end,sku=None,sort_by='contribution_profit',descending=True):
    if start>end: raise ValueError('start_date must not exceed end_date')
    result=[]
    for code in skus(session,store_id,sku):
        sales=facts(session,SalesRecord,store_id,start,end,code)
        ads=facts(session,AdRecord,store_id,start,end,code)
        costs=list(session.scalars(select(CostRecord).where(CostRecord.store_id==store_id,CostRecord.sku==code,CostRecord.effective_from<=end).order_by(CostRecord.effective_from)))
        gross=sum((r.gross_sales for r in sales),ZERO); refunds=sum((r.refund_amount for r in sales),ZERO)
        spend=sum((r.spend for r in ads),ZERO)
        reasons=[]; purchase=logistics=fees=ZERO
        currencies={r.currency for r in sales+ads}
        used=[]
        for row in sorted(sales,key=lambda r:r.record_date):
            if not row.quantity: continue
            applicable=[c for c in costs if c.effective_from<=row.record_date]
            if not applicable:
                reasons.append('missing_cost'); continue
            c=applicable[-1]; currencies.add(c.currency); used.append(c)
            purchase+=c.purchase_cost*row.quantity; logistics+=c.logistics_cost*row.quantity; fees+=c.platform_fee_per_unit*row.quantity
        from app.models import Store
        currency=session.get(Store,store_id).currency
        if currencies-{currency}: reasons.append('currency_mismatch')
        net=gross-refunds
        if not sales: reasons.append('no_sales')
        complete=not reasons
        profit=net-purchase-logistics-fees-spend if complete else None
        margin=ratio(profit,net) if profit is not None else None
        if net<=0: reasons.append('nonpositive_net_revenue')
        result.append(dict(sku=code,quantity=sum(r.quantity for r in sales),gross_sales=gross,refund_amount=refunds,net_revenue=net,purchase_cost=purchase if complete else None,logistics_cost=logistics if complete else None,platform_fees=fees if complete else None,ad_spend=spend,contribution_profit=profit,profit_margin=margin,reasons=sorted(set(reasons)),cost_increased=any(b.purchase_cost+b.logistics_cost+b.platform_fee_per_unit>a.purchase_cost+a.logistics_cost+a.platform_fee_per_unit for a,b in zip(used,used[1:]))))
    if sort_by not in ('contribution_profit','net_revenue','profit_margin'): raise ValueError('unsupported sort')
    valid=[r for r in result if r[sort_by] is not None]; missing=[r for r in result if r[sort_by] is None]
    return sorted(valid,key=lambda r:r[sort_by],reverse=descending)+missing
