from datetime import datetime
from sqlalchemy import String,DateTime,ForeignKeyConstraint,CheckConstraint,Index,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from app.models.agent_task import TaskBase,now
from app.models.decision import DecisionProposal

class DecisionAudit(TaskBase):
    __tablename__='decision_audits'
    __table_args__=(ForeignKeyConstraint(['proposal_id','store_id'],['decision_proposals.proposal_id','decision_proposals.store_id'],ondelete='RESTRICT'),UniqueConstraint('proposal_id','action',name='uq_decision_audit_action'),CheckConstraint("(action='submit' AND from_status='draft' AND to_status='pending_review') OR (action='approve' AND from_status='pending_review' AND to_status='approved') OR (action='reject' AND from_status='pending_review' AND to_status='rejected')",name='ck_audit_transition'),Index('ix_audit_proposal_created','proposal_id','created_at'))
    audit_id: Mapped[str]=mapped_column(String(36),primary_key=True)
    proposal_id: Mapped[str]=mapped_column(String(36))
    store_id: Mapped[int]
    action: Mapped[str]=mapped_column(String(20))
    from_status: Mapped[str]=mapped_column(String(20))
    to_status: Mapped[str]=mapped_column(String(20))
    reviewer_id: Mapped[str]=mapped_column(String(100))
    identity_source: Mapped[str]=mapped_column(String(30))
    comment: Mapped[str]=mapped_column(String(2000))
    created_at: Mapped[datetime]=mapped_column(DateTime,default=now)
