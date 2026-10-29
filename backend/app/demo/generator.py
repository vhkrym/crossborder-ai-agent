"""Deterministic demo rows. Inventory is end-of-day; receipts precede sales."""
from datetime import date, timedelta
from decimal import Decimal as D
from random import Random

from app.core.money import normalize_money as money

DEFAULT_START = date(2026, 1, 1)

def generate(seed=42, start=DEFAULT_START, days=90):
    rng = Random(seed)
    data = {name: [] for name in ('stores','products','sales_records','ad_records','inventory_snapshots','cost_records')}
    for store in (1,2):
        data['stores'].append(dict(id=store,name=f'DEMO Amazon US {store}',marketplace='Amazon',market='US',currency='USD'))
    for n in range(30):
        store = n // 15 + 1
        sku = f'DEMO-{n+1:03d}'
        key = dict(store_id=store,sku=sku)
        data['products'].append(dict(id=n+1,**key))
        price = D(20 + n % 8 * 3)
        base = 45 if n == 0 else (0 if n == 3 else 8 + n % 9)
        purchase = D('15.5') if n == 0 else price * D('0.30')
        for offset, cost in [(0,purchase)] + ([(45,purchase + D('7'))] if n in (4,9,19) and days > 45 else []):
            data['cost_records'].append(dict(**key,effective_from=start+timedelta(days=offset),purchase_cost=money(cost),logistics_cost=D('1.5'),platform_fee_per_unit=money(price*D('0.15')),currency='USD'))
        stock = 800 if n == 3 else base * days + 100
        if n == 2: stock = 35
        pending = []
        history = []
        for day in range(days):
            current = start + timedelta(days=day)
            receipts = sum(q for arrival,q in pending if arrival == day)
            pending = [(arrival,q) for arrival,q in pending if arrival > day]
            stock += receipts
            weekend = D('1.20') if current.weekday() >= 5 else D('1')
            promo = 30 <= day < 37
            demand = int(D(base) * weekend * (D('1')+D(day)/D('450')) * (D('1.5') if promo else D('1')))+rng.randint(0,3)
            if n == 3: demand = 1 if day % 20 == 0 else 0
            quantity = min(stock,demand)
            # SKU 003 has a delayed replenishment that will not arrive in this horizon.
            stock -= quantity
            if n == 2 and not pending: pending.append((days+10,200))
            elif n != 2 and stock < base*14 and not pending: pending.append((day+10,base*30))
            unit_price = price * (D('0.90') if promo else D('1'))
            gross = money(unit_price * quantity)
            refund = money(unit_price * (history[day-7] // 20 if day >= 7 else 0))
            if n == 2 and day == 10: refund = money(price*2)  # refund of earlier orders
            history.append(quantity)
            data['sales_records'].append(dict(**key,record_date=current,quantity=quantity,gross_sales=gross,refund_amount=refund,currency='USD'))
            clicks = max(0,quantity*3+rng.randint(0,12))
            orders = min(clicks,quantity//3 + rng.randint(0,2))
            cpc = D('3.50') if n == 1 else D('0.25')+D(rng.randint(0,20))/100
            spend = money(clicks*cpc)
            attributed = money(orders*unit_price*(D('1')+D(rng.randint(0,10))/100))
            data['ad_records'].append(dict(**key,record_date=current,spend=spend,attributed_sales=attributed,clicks=clicks,orders=orders,currency='USD'))
            data['inventory_snapshots'].append(dict(**key,snapshot_date=current,on_hand=stock,reserved=min(stock,quantity//5),inbound=sum(q for _,q in pending),lead_time_days=10))
    return data
