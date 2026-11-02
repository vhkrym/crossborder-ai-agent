from app.schemas.simulations import SimulationInput,SimulationOutput

ACTIONS={
'profit_review':('profit_review_ticket','已创建本地利润复核模拟工单。'),
'ad_budget_review':('ad_optimization_assessment','已创建本地广告投放优化评估模拟工单。'),
'replenishment_review':('replenishment_plan_draft','已创建本地补货计划评估草案，数量待人工核实。'),
'overstock_review':('stock_clearance_assessment','已创建本地库存清理评估模拟工单。'),
'cost_change_review':('cost_review_ticket','已创建本地成本复核模拟工单。')}
LIMITS=['simulation_only=true：仅本地模拟，不修改实际经营数据。','未调用任何外部平台接口，未调整预算、价格、库存或成本。','不提供预计收益、ACOS改善或新增补货数量。','工单生成不代表经营目标实现。']

def simulate(snapshot:SimulationInput)->SimulationOutput:
    p=snapshot.proposal
    if p.status!='approved' or snapshot.approval.action!='approve' or snapshot.approval.proposal_id!=p.proposal_id or snapshot.approval.store_id!=p.store_id:raise ValueError('invalid_approved_snapshot')
    action,summary=ACTIONS[p.proposal_type]
    return SimulationOutput(action_type=action,proposal_id=p.proposal_id,source_task_id=p.source_task_id,store_id=p.store_id,sku=p.sku,summary=summary,input_basis={'evidence':p.evidence_json.model_dump(mode='json'),'approval_audit_id':str(snapshot.approval.audit_id)},limitations=LIMITS)
