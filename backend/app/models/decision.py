from datetime import datetime
from sqlalchemy import ForeignKeyConstraint, UniqueConstraint, CheckConstraint, Index, String, JSON, DateTime
from sqlalchemy.orm import Mapped,mapped_column
from app.models.agent_task import TaskBase,now

class DecisionProposal(TaskBase):
    __tablename__='decision_proposals'
    __table_args__=(ForeignKeyConstraint(['source_task_id','store_id'],['agent_tasks.task_id','agent_tasks.store_id'],ondelete='RESTRICT'),UniqueConstraint('source_task_id','sku','proposal_type',name='uq_decision_identity'),CheckConstraint("status IN ('draft','pending_review','approved','rejected')",name='ck_decision_status'),CheckConstraint("proposal_type IN ('profit_review','ad_budget_review','replenishment_review','overstock_review','cost_change_review')",name='ck_decision_type'),CheckConstraint("risk_level IN ('high','medium','low')",name='ck_decision_risk'),Index('ix_decision_store_created','store_id','created_at'),Index('ix_decision_status','status'))
    proposal_id: Mapped[str]=mapped_column(String(36),primary_key=True)
    source_task_id: Mapped[str]=mapped_column(String(36),index=True)
    store_id: Mapped[int]
    sku: Mapped[str]=mapped_column(String(100))
    proposal_type: Mapped[str]=mapped_column(String(40))
    title: Mapped[str]=mapped_column(String(200))
    description: Mapped[str]=mapped_column(String(1000))
    risk_level: Mapped[str]=mapped_column(String(10))
    suggested_action: Mapped[str]=mapped_column(String(1000))
    evidence_json: Mapped[dict]=mapped_column(JSON)
    limitations_json: Mapped[list]=mapped_column(JSON)
    status: Mapped[str]=mapped_column(String(20),default='pending_review')
    created_at: Mapped[datetime]=mapped_column(DateTime,default=now)
    updated_at: Mapped[datetime]=mapped_column(DateTime,default=now)


class DecisionGeneration(TaskBase):
    """Freeze even a zero-proposal generation result for idempotency."""
    __tablename__='decision_generations'
    source_task_id: Mapped[str]=mapped_column(__import__('sqlalchemy').ForeignKey('agent_tasks.task_id',ondelete='RESTRICT'),primary_key=True)
    generated_at: Mapped[datetime]=mapped_column(DateTime,default=now)
    skipped_json: Mapped[list]=mapped_column(JSON)
