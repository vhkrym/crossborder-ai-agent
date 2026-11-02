from uuid import uuid4
from sqlalchemy import select,update,text
from app.db.session import SessionLocal
from app.models.agent_task import now
from app.models.decision import DecisionProposal
from app.models.decision_audit import DecisionAudit
from app.schemas.decisions import Proposal
from app.schemas.decision_approvals import Audit
from app.services.agent_tasks import scrub

TRANSITIONS={'submit':('draft','pending_review'),'approve':('pending_review','approved'),'reject':('pending_review','rejected')}
class ApprovalService:
    def __init__(self,factory=SessionLocal):self.factory=factory
    def review(self,id,store_id,action,comment):
        if action not in TRANSITIONS:raise ValueError('invalid_action')
        comment=comment.strip()
        if action=='reject' and not comment:raise ValueError('rejection_reason_required')
        if len(comment)>2000:raise ValueError('comment_too_long')
        before,after=TRANSITIONS[action]
        with self.factory() as s:
            if s.get_bind().dialect.name=='sqlite':s.execute(text('BEGIN IMMEDIATE'))
            row=s.get(DecisionProposal,str(id))
            if not row or row.store_id!=store_id:raise LookupError('proposal_not_found')
            changed=s.execute(update(DecisionProposal).where(DecisionProposal.proposal_id==str(id),DecisionProposal.store_id==store_id,DecisionProposal.status==before).values(status=after,updated_at=now()))
            if changed.rowcount!=1:raise RuntimeError('invalid_or_already_reviewed_state')
            audit=DecisionAudit(audit_id=str(uuid4()),proposal_id=str(id),store_id=row.store_id,action=action,from_status=before,to_status=after,reviewer_id='local-demo-reviewer',identity_source='local_demo',comment=scrub(comment or ('已人工确认：批准仅代表审核，不代表执行。' if action=='approve' else '提交人工审核。')))
            s.add(audit);s.flush();s.refresh(row)
            result=dict(proposal=Proposal.model_validate(row),audit=Audit.model_validate(audit));s.commit();return result
    def audit(self,id,store_id):
        with self.factory() as s:
            row=s.get(DecisionProposal,str(id))
            if not row or row.store_id!=store_id:raise LookupError('proposal_not_found')
            return [Audit.model_validate(r) for r in s.scalars(select(DecisionAudit).where(DecisionAudit.proposal_id==str(id),DecisionAudit.store_id==store_id).order_by(DecisionAudit.created_at,DecisionAudit.audit_id))]
