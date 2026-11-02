from uuid import uuid4
from datetime import timedelta
from app.models import CostRecord
from sqlalchemy import select,func,text
from app.db.session import SessionLocal
from app.models.agent_task import AgentTask,now
from app.models.decision import DecisionProposal,DecisionGeneration
from app.schemas.agent_tasks import TaskTrace
from app.agents.supervisor_state import Report
from app.services.analytics import analyze
from app.analytics.decisions import evaluate,RULES,THRESHOLDS
from app.schemas.decisions import Proposal

class DecisionService:
    def __init__(self,factory=SessionLocal):self.factory=factory
    def generate(self,task_id):
        with self.factory() as s:
            # Single SQLite snapshot + serialize competing generators before reading.
            if s.get_bind().dialect.name=='sqlite':s.execute(text('BEGIN IMMEDIATE'))
            task=s.get(AgentTask,str(task_id))
            if not task:raise LookupError('task_not_found')
            if task.status!='completed' or not task.report_json:raise ValueError('completed_verified_task_required')
            Report.model_validate(task.report_json);trace=TaskTrace.model_validate(task.trace_json)
            if not trace.route or trace.route.selected_agents!=task.selected_agents:raise ValueError('invalid_task_trace')
            generation=s.get(DecisionGeneration,str(task_id))
            if generation:
                existing=list(s.scalars(select(DecisionProposal).where(DecisionProposal.source_task_id==str(task_id))))
                return dict(source_task_id=task_id,store_id=task.store_id,proposals=[Proposal.model_validate(p) for p in existing],skipped_reasons=generation.skipped_json,reused=True)
            data={};skipped=[]
            for agent in task.selected_agents:
                matching=[t for t in trace.tools if t.tool=='analyze_'+agent and t.status in ('success','warning')]
                if not matching:raise ValueError('missing_verified_tool_trace')
                params=matching[-1].parameters
                if not params or (params.store_id,params.start_date,params.end_date,params.selected_sku)!=(task.store_id,task.start_date,task.end_date,task.selected_sku):raise ValueError('task_scope_mismatch')
                r=analyze(s,agent,task.store_id,task.start_date,task.end_date,task.selected_sku,params.window,params.safety_days)
                data[agent]=getattr(r,agent)
            candidates,skipped=evaluate(data)
            cost_evidence={}
            for row in data.get('profit',[]):
                if not row.cost_increased:continue
                versions=list(s.scalars(select(CostRecord).where(CostRecord.store_id==task.store_id,CostRecord.sku==row.sku,CostRecord.effective_from<=task.end_date).order_by(CostRecord.effective_from)))
                for before,after in zip(versions,versions[1:]):
                    change=after.effective_from
                    if change<=task.start_date:continue
                    if before.currency!=after.currency:continue
                    old_total=before.purchase_cost+before.logistics_cost+before.platform_fee_per_unit
                    new_total=after.purchase_cost+after.logistics_cost+after.platform_fee_per_unit
                    if new_total-old_total<=THRESHOLDS['unit_cost_increase']:continue
                    pre=analyze(s,'profit',task.store_id,task.start_date,change-timedelta(days=1),row.sku).profit[0]
                    post=analyze(s,'profit',task.store_id,change,task.end_date,row.sku).profit[0]
                    if pre.profit_margin is not None and post.profit_margin is not None and pre.profit_margin-post.profit_margin>THRESHOLDS['margin_decline']:
                        candidates.append(('cost_change_review',row))
                        cost_evidence[row.sku]=dict(previous_cost_date=str(before.effective_from),new_cost_date=str(change),previous_unit_cost=str(old_total),new_unit_cost=str(new_total),before_period=pre.model_dump(mode='json'),after_period=post.model_dump(mode='json'),comparison='cost rose and observed contribution margin declined; causality not proven')
                        skipped.remove(f'{row.sku}:cost_change_requires_historical_margin_comparison')
                        break
            existing=list(s.scalars(select(DecisionProposal).where(DecisionProposal.source_task_id==str(task_id))))
            if existing:return dict(source_task_id=task_id,store_id=task.store_id,proposals=[Proposal.model_validate(p) for p in existing],skipped_reasons=skipped,reused=True)
            generated=now();rows=[]
            for kind,row in candidates:
                title,action,risk=RULES[kind];agent={'profit_review':'profit','ad_budget_review':'advertising','replenishment_review':'inventory','overstock_review':'inventory','cost_change_review':'profit'}[kind]
                proposal=DecisionProposal(proposal_id=str(uuid4()),source_task_id=task.task_id,store_id=task.store_id,sku=row.sku,proposal_type=kind,title=title,description='基于生成时点的确定性分析结果触发；仅供人工审核，尚未执行。',risk_level=risk,suggested_action=action,evidence_json=dict(schema_version='1',generated_at=generated.isoformat(),store_id=task.store_id,source_task_id=task.task_id,start_date=str(task.start_date),end_date=str(task.end_date),tool='analyze_'+agent,metrics={**row.model_dump(mode='json'),**({'historical_comparison':cost_evidence[row.sku]} if kind=='cost_change_review' else {})}),limitations_json=['生成时重新分析，不是原任务完成时的数据快照。','仅供人工审核，尚未执行；不自动确定预算、补货量或收益。']+list(row.reasons),status='pending_review')
                s.add(proposal);rows.append(proposal)
            skipped=skipped or ([] if rows else ['no_proven_trigger'])
            s.add(DecisionGeneration(source_task_id=task.task_id,generated_at=generated,skipped_json=skipped))
            s.flush();response=dict(source_task_id=task_id,store_id=task.store_id,proposals=[Proposal.model_validate(p) for p in rows],skipped_reasons=skipped or ([] if rows else ['no_proven_trigger']),reused=False)
            s.commit();return response
    def list(self,store_id,kind,status,risk,page,size):
        with self.factory() as s:
            q=select(DecisionProposal).where(DecisionProposal.store_id==store_id)
            for attr,val in [('proposal_type',kind),('status',status),('risk_level',risk)]:
                if val:q=q.where(getattr(DecisionProposal,attr)==val)
            total=s.scalar(select(func.count()).select_from(q.subquery()))
            return dict(items=[Proposal.model_validate(p) for p in s.scalars(q.order_by(DecisionProposal.created_at.desc(),DecisionProposal.proposal_id.desc()).offset((page-1)*size).limit(size))],total=total,page=page,page_size=size)
    def get(self,id):
        with self.factory() as s:
            row=s.get(DecisionProposal,str(id))
            if not row:raise LookupError('proposal_not_found')
            return Proposal.model_validate(row)
