from datetime import date, datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.agents.supervisor_state import Report, RouteDecision
from app.agents.trace import ExecutionTrace

TaskStatus=Literal['queued','running','completed','partial_failed','failed','unsupported','interrupted']
class TaskCreate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    store_id: int=Field(gt=0)
    user_query: str=Field(min_length=1,max_length=4000)
    start_date: date
    end_date: date
    selected_sku: str | None=Field(default=None,min_length=1,max_length=100)
    @model_validator(mode='after')
    def validate_input(self):
        if self.start_date>self.end_date: raise ValueError('invalid date range')
        if not self.user_query.strip() or self.selected_sku is not None and not self.selected_sku.strip():raise ValueError('blank input')
        return self

class TaskCreated(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    task_id: UUID
    status: TaskStatus
    created_at: datetime

class TaskTrace(BaseModel):
    schema_version: str='1'
    route: RouteDecision | None=None
    tools: list[ExecutionTrace]=Field(default_factory=list)

class TaskDetail(TaskCreated):
    store_id: int
    user_query: str
    start_date: date
    end_date: date
    selected_sku: str | None
    selected_agents: list[str]
    intent: str | None
    report_json: Report | None
    trace_json: TaskTrace
    error_code: str | None
    error_summary: str | None
    started_at: datetime | None
    finished_at: datetime | None
    updated_at: datetime

class TaskPage(BaseModel):
    items: list[TaskDetail]
    total: int
    page: int
    page_size: int
