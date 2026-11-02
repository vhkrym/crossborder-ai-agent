from decimal import Decimal

THRESHOLDS={'acos':Decimal('1'),'coverage_days':Decimal('365'),'profit':Decimal('0'),'unit_cost_increase':Decimal('0'),'margin_decline':Decimal('0')}
RULES={
'profit_review':('负贡献利润复核','复核定价、采购成本和退款原因。','high'),
'ad_budget_review':('高 ACOS 投放复核','人工检查投放策略与预算，不自动调整预算。','high'),
'replenishment_review':('缺货风险复核','人工复核需求和补货计划，不自动确定采购量。','high'),
'overstock_review':('库存积压复核','评估促销和库存处理方案，不承诺收益。','medium'),
'cost_change_review':('成本变化复核','复核采购成本及价格策略。','medium')}

def evaluate(data):
    candidates=[];skipped=[]
    def add(kind,row):candidates.append((kind,row))
    for row in data.get('profit',[]):
        if row.contribution_profit is not None and 'currency_mismatch' not in row.reasons and row.contribution_profit<THRESHOLDS['profit']:add('profit_review',row)
        elif row.contribution_profit is None:skipped.append(f'{row.sku}:profit_unavailable')
        if row.cost_increased:skipped.append(f'{row.sku}:cost_change_requires_historical_margin_comparison')
    for row in data.get('advertising',[]):
        if row.acos is not None and row.acos>THRESHOLDS['acos']:add('ad_budget_review',row)
        elif row.acos is None:skipped.append(f'{row.sku}:acos_unavailable')
    for row in data.get('inventory',[]):
        if row.risk in ('stockout','at_risk'):add('replenishment_review',row)
        if row.coverage_days is not None and row.snapshot_date is not None and not any(r in row.reasons for r in ('stale_snapshot','insufficient_history')) and row.coverage_days>THRESHOLDS['coverage_days']:add('overstock_review',row)
        if row.risk=='unknown':skipped.append(f'{row.sku}:inventory_unavailable')
    return candidates,skipped
