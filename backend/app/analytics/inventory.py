from datetime import timedelta
from decimal import Decimal, ROUND_CEILING
from sqlalchemy import select
from app.models import InventorySnapshot, SalesRecord
from app.analytics.common import skus, ratio

def analyze_inventory(session,store_id,end,sku=None,window=30,safety_days=7):
    if not 1<=window<=365 or not 0<=safety_days<=365: raise ValueError('invalid inventory configuration')
    start=end-timedelta(days=window-1); result=[]
    for code in skus(session,store_id,sku):
        snap=session.scalar(select(InventorySnapshot).where(InventorySnapshot.store_id==store_id,InventorySnapshot.sku==code,InventorySnapshot.snapshot_date<=end).order_by(InventorySnapshot.snapshot_date.desc()).limit(1))
        rows=list(session.scalars(select(SalesRecord).where(SalesRecord.store_id==store_id,SalesRecord.sku==code,SalesRecord.record_date>=start,SalesRecord.record_date<=end)))
        observed=len({r.record_date for r in rows}); reasons=[]
        if observed<window: reasons.append('insufficient_history')
        avg=Decimal(sum(r.quantity for r in rows))/window if observed==window else None
        if avg==0: reasons.append('zero_sales')
        if not snap: reasons.append('missing_snapshot')
        elif snap.snapshot_date!=end: reasons.append('stale_snapshot')
        available=snap.available if snap else None
        coverage=ratio(Decimal(available),avg) if available is not None and avg is not None else None
        risk='unknown'; replenish=None
        if snap and snap.snapshot_date==end and avg is not None:
            target=avg*(snap.lead_time_days+safety_days)
            replenish=max(0,int((target-available).to_integral_value(rounding=ROUND_CEILING)))
            if available==0 and avg==0:
                reasons.append('demand_censored_by_stockout')
                replenish=None
            risk='stockout' if available==0 else ('zero_sales_stock' if avg==0 else ('at_risk' if available<target else ('slow_moving_stock' if coverage is not None and coverage>365 else 'healthy')))
        result.append(dict(sku=code,snapshot_date=snap.snapshot_date if snap else None,on_hand=snap.on_hand if snap else None,reserved=snap.reserved if snap else None,available=available,inbound=snap.inbound if snap else None,lead_time_days=snap.lead_time_days if snap else None,observed_days=observed,average_daily_sales=avg,coverage_days=coverage,risk=risk,suggested_replenishment=replenish,reasons=reasons))
    return result
