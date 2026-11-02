from uuid import uuid4
from sqlalchemy import select,update,func,text,inspect
from app.db.session import SessionLocal
from app.models.agent_task import now
from app.models.decision import DecisionProposal
from app.models.decision_audit import DecisionAudit
from app.models.decision_simulation import DecisionSimulation
from app.schemas.simulations import SimulationInput,SimulationDetail,SimulationOutput
from app.schemas.decisions import Proposal
from app.schemas.decision_approvals import Audit
from app.services.simulation_engine import simulate,ACTIONS,LIMITS

class SimulationService:
    def __init__(self,factory=SessionLocal,runner=simulate):self.factory=factory;self.runner=runner
    def create(self,proposal_id):
        with self.factory() as s:
            s.execute(text('BEGIN IMMEDIATE'))
            proposal=s.get(DecisionProposal,str(proposal_id))
            if not proposal:raise LookupError('proposal_not_found')
            if proposal.status!='approved':raise ValueError('approved_proposal_required')
            existing=s.scalar(select(DecisionSimulation).where(DecisionSimulation.proposal_id==str(proposal_id)))
            if existing:return dict(simulation_id=existing.simulation_id,status=existing.status,reused=True)
            audit=s.scalar(select(DecisionAudit).where(DecisionAudit.proposal_id==str(proposal_id),DecisionAudit.store_id==proposal.store_id,DecisionAudit.action=='approve',DecisionAudit.to_status=='approved'))
            if not audit:raise ValueError('approval_audit_required')
            snapshot=SimulationInput(proposal=Proposal.model_validate(proposal),approval=Audit.model_validate(audit))
            row=DecisionSimulation(simulation_id=str(uuid4()),proposal_id=proposal.proposal_id,source_task_id=proposal.source_task_id,approval_audit_id=audit.audit_id,store_id=proposal.store_id,sku=proposal.sku,proposal_type=proposal.proposal_type,action_type=ACTIONS[proposal.proposal_type][0],status='pending',input_snapshot_json=snapshot.model_dump(mode='json'),limitations_json=LIMITS)
            s.add(row);s.flush();id=row.simulation_id;s.commit()
        self.execute(id)
        return dict(simulation_id=id,status=self.get(id).status,reused=False)
    def execute(self,id):
        with self.factory() as s:
            claimed=s.execute(update(DecisionSimulation).where(DecisionSimulation.simulation_id==str(id),DecisionSimulation.status=='pending').values(status='running',started_at=now()))
            s.commit()
            if claimed.rowcount!=1:return False
            row=s.get(DecisionSimulation,str(id));raw_snapshot=row.input_snapshot_json
        try:
            snapshot=SimulationInput.model_validate(raw_snapshot)
            output=SimulationOutput.model_validate(self.runner(snapshot))
            p=snapshot.proposal
            if (str(output.proposal_id),str(output.source_task_id),output.store_id,output.sku,output.action_type)!=(str(p.proposal_id),str(p.source_task_id),p.store_id,p.sku,ACTIONS[p.proposal_type][0]):raise ValueError('output_scope_mismatch')
            values=dict(status='simulation_completed',output_json=output.model_dump(mode='json'),finished_at=now())
        except Exception:values=dict(status='simulation_failed',error_code='simulation_engine_error',error_summary='本地模拟工单生成失败，未执行经营动作。',finished_at=now())
        with self.factory() as s:
            s.execute(update(DecisionSimulation).where(DecisionSimulation.simulation_id==str(id),DecisionSimulation.status=='running').values(**values));s.commit()
        return True
    def get(self,id):
        with self.factory() as s:
            row=s.get(DecisionSimulation,str(id))
            if not row:raise LookupError('simulation_not_found')
            return SimulationDetail.model_validate(row)
    def list(self,store_id,status,kind,page,size):
        with self.factory() as s:
            q=select(DecisionSimulation).where(DecisionSimulation.store_id==store_id)
            if status:q=q.where(DecisionSimulation.status==status)
            if kind:q=q.where(DecisionSimulation.proposal_type==kind)
            total=s.scalar(select(func.count()).select_from(q.subquery()))
            return dict(items=[SimulationDetail.model_validate(r) for r in s.scalars(q.order_by(DecisionSimulation.created_at.desc(),DecisionSimulation.simulation_id.desc()).offset((page-1)*size).limit(size))],total=total,page=page,page_size=size)
    def recover(self):
        with self.factory() as s:
            if not inspect(s.get_bind()).has_table('decision_simulations'):return 0
            r=s.execute(update(DecisionSimulation).where(DecisionSimulation.status.in_(['pending','running'])).values(status='interrupted',error_code='process_restarted',error_summary='进程中断；本版本不自动重试或恢复。',finished_at=now()));s.commit();return r.rowcount
