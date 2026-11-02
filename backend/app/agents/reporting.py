from app.agents.supervisor_state import Evidence, Report

METRICS={'profit':['quantity','net_revenue','contribution_profit','profit_margin','cost_increased'],'advertising':['spend','attributed_sales','acos','roas','cpc','conversion_rate'],'inventory':['available','inbound','coverage_days','suggested_replenishment','risk']}
LABELS={'quantity':'售出件数','net_revenue':'净销售收入','contribution_profit':'贡献利润','profit_margin':'贡献利润率','cost_increased':'成本上涨','spend':'广告支出','attributed_sales':'广告归因销售额','acos':'ACOS','roas':'ROAS','cpc':'CPC','conversion_rate':'广告转化率','available':'可售库存','inbound':'在途库存','coverage_days':'库存覆盖天数','suggested_replenishment':'建议补货量','risk':'库存状态'}

def collect(agent,result):
    if result.data is None:return {}
    group={'profit':'profit','advertising':'advertising','inventory':'inventory'}[agent]
    evidence={}
    for index,row in enumerate(getattr(result.data,group)):
        values=row.model_dump(mode='json')
        for metric in METRICS[agent]:
            identifier=f'{agent}:{index}:{metric}'
            value=values[metric]
            if isinstance(value,bool):value='是' if value else '否'
            unit='比例' if metric in ('profit_margin','acos','conversion_rate') else ('天' if metric=='coverage_days' else ('件' if metric in ('available','inbound','suggested_replenishment') else result.data.currency if metric in ('net_revenue','contribution_profit','spend','attributed_sales','cpc') else ''))
            evidence[identifier]=Evidence(id=identifier,agent=agent,sku=row.sku,metric=metric,value=value,unit=unit,source=f'tool_results.{result.tool}.data.{group}[{index}].{metric}')
    return evidence

def render_report(state,ids):
    # Model may select evidence, never supply narrative numbers or actions.
    if not ids or any(i not in state.evidence for i in ids):raise ValueError('invalid_evidence_reference')
    findings=[]
    for i in dict.fromkeys(ids):
        e=state.evidence[i]
        findings.append(f'{e.sku}：{LABELS[e.metric]} = {e.value if e.value is not None else "不可计算"} {e.unit} [{i}]')
    risks=[];limits=['贡献利润不是财务净利润；退款不改变销量。','广告归因额不是店铺销售额；比例以小数表示。','库存无预计到货日期，在途不算可售；缺乏需求依据时不推断补货。','不同指标口径不可互相替代；结论冲突时保留各自证据，不自动裁决。']
    for tool,r in state.tool_results.items():
        risks.extend(r.anomalies)
        if r.error:limits.append(f'{tool} 失败：{r.error}；报告不包含其指标。')
    limits.extend(state.errors)
    return Report(problem_understanding=f'在可信店铺和日期范围内分析：{state.route.intent}',key_findings=findings,business_risks=risks or ['暂无规则识别的异常，不代表无风险。'],suggested_actions=['建议人工复核异常 SKU 的成本、投放或补货依据；本次未执行经营动作。'],evidence_and_limits=limits,evidence_ids=list(dict.fromkeys(ids)))
