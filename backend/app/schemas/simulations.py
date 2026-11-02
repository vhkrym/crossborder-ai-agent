from datetime import datetime
from uuid import UUID
from typing import Literal
from pydantic import BaseModel,ConfigDict
from app.schemas.decisions import Proposal,ProposalType
from app.schemas.decision_approvals import Audit

SimulationStatus=Literal['pending','running','simulation_completed','simulation_failed','interrupted']
class EmptySimulationRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
class SimulationInput(BaseModel):
    schema_version: str='1'
    proposal: Proposal
    approval: Audit
class SimulationOutput(BaseModel):
    simulation_only: Literal[True]=True
    action_type: str
    proposal_id: UUID
    source_task_id: UUID
    store_id: int
    sku: str
    summary: str
    input_basis: dict
    limitations: list[str]
class SimulationDetail(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    simulation_id: UUID
    proposal_id: UUID
    source_task_id: UUID
    approval_audit_id: UUID
    store_id: int
    sku: str
    proposal_type: ProposalType
    action_type: str
    status: SimulationStatus
    input_snapshot_json: SimulationInput
    output_json: SimulationOutput | None
    limitations_json: list[str]
    error_code: str | None
    error_summary: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
class SimulationCreated(BaseModel):
    simulation_id: UUID
    status: SimulationStatus
    reused: bool
class SimulationPage(BaseModel):
    items: list[SimulationDetail]
    total: int
    page: int
    page_size: int
