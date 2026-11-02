from datetime import datetime
from sqlalchemy import String,JSON,DateTime,ForeignKey,ForeignKeyConstraint,CheckConstraint,Index,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from app.models.agent_task import TaskBase,now
from app.models.decision import DecisionProposal
from app.models.decision_audit import DecisionAudit

class DecisionSimulation(TaskBase):
    __tablename__='decision_simulations'
    __table_args__=(ForeignKeyConstraint(['proposal_id','store_id'],['decision_proposals.proposal_id','decision_proposals.store_id'],ondelete='RESTRICT'),UniqueConstraint('proposal_id',name='uq_simulation_proposal'),CheckConstraint("status IN ('pending','running','simulation_completed','simulation_failed','interrupted')",name='ck_simulation_status'),Index('ix_simulation_store_created','store_id','created_at'),Index('ix_simulation_status','status'))
    simulation_id: Mapped[str]=mapped_column(String(36),primary_key=True)
    proposal_id: Mapped[str]=mapped_column(String(36))
    source_task_id: Mapped[str]=mapped_column(ForeignKey('agent_tasks.task_id',ondelete='RESTRICT'))
    approval_audit_id: Mapped[str]=mapped_column(ForeignKey('decision_audits.audit_id',ondelete='RESTRICT'))
    store_id: Mapped[int]
    sku: Mapped[str]=mapped_column(String(100))
    proposal_type: Mapped[str]=mapped_column(String(40))
    action_type: Mapped[str]=mapped_column(String(60))
    status: Mapped[str]=mapped_column(String(30),default='pending')
    input_snapshot_json: Mapped[dict]=mapped_column(JSON)
    output_json: Mapped[dict | None]=mapped_column(JSON)
    limitations_json: Mapped[list]=mapped_column(JSON)
    error_code: Mapped[str | None]=mapped_column(String(100))
    error_summary: Mapped[str | None]=mapped_column(String(500))
    created_at: Mapped[datetime]=mapped_column(DateTime,default=now)
    started_at: Mapped[datetime | None]=mapped_column(DateTime)
    finished_at: Mapped[datetime | None]=mapped_column(DateTime)
