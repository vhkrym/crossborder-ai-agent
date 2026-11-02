from datetime import date, datetime, timezone
from sqlalchemy import CheckConstraint, Index, ForeignKey, String, JSON, Date, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from app.models import Store

def now(): return datetime.now(timezone.utc).replace(tzinfo=None)

class TaskBase(DeclarativeBase): pass

class AgentTask(TaskBase):
    __tablename__='agent_tasks'
    __table_args__=(CheckConstraint("status IN ('queued','running','completed','partial_failed','failed','unsupported','interrupted')",name='ck_agent_task_status'),Index('ix_agent_tasks_store_created','store_id','created_at'),Index('ix_agent_tasks_status_created','status','created_at'))
    task_id: Mapped[str]=mapped_column(String(36),primary_key=True)
    store_id: Mapped[int]=mapped_column(ForeignKey(Store.id,ondelete='RESTRICT'))
    user_query: Mapped[str]=mapped_column(String(4000))
    start_date: Mapped[date]=mapped_column(Date)
    end_date: Mapped[date]=mapped_column(Date)
    selected_sku: Mapped[str | None]=mapped_column(String(100))
    status: Mapped[str]=mapped_column(String(20),default='queued')
    selected_agents: Mapped[list]=mapped_column(JSON,default=list)
    intent: Mapped[str | None]=mapped_column(String(20))
    report_json: Mapped[dict | None]=mapped_column(JSON)
    trace_json: Mapped[dict]=mapped_column(JSON,default=dict)
    error_code: Mapped[str | None]=mapped_column(String(100))
    error_summary: Mapped[str | None]=mapped_column(String(500))
    created_at: Mapped[datetime]=mapped_column(DateTime,default=now)
    started_at: Mapped[datetime | None]=mapped_column(DateTime)
    finished_at: Mapped[datetime | None]=mapped_column(DateTime)
    updated_at: Mapped[datetime]=mapped_column(DateTime,default=now)
