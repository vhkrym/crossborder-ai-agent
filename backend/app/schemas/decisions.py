from datetime import datetime
from uuid import UUID
from typing import Literal,Any
from pydantic import BaseModel,ConfigDict,Field

ProposalType=Literal['profit_review','ad_budget_review','replenishment_review','overstock_review','cost_change_review']
class GenerateRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    source_task_id: UUID
class EvidenceSnapshot(BaseModel):
    schema_version: str
    generated_at: datetime
    store_id: int
    source_task_id: UUID
    start_date: str
    end_date: str
    tool: str
    metrics: dict[str,Any]
class Proposal(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    proposal_id: UUID
    source_task_id: UUID
    store_id: int
    sku: str
    proposal_type: ProposalType
    title: str
    description: str
    risk_level: Literal['high','medium','low']
    suggested_action: str
    evidence_json: EvidenceSnapshot
    limitations_json: list[str]
    status: Literal['draft','pending_review','approved','rejected']
    created_at: datetime
    updated_at: datetime
class GenerateResponse(BaseModel):
    source_task_id: UUID
    store_id: int
    proposals: list[Proposal]
    skipped_reasons: list[str]
    reused: bool
class ProposalPage(BaseModel):
    items: list[Proposal]
    total: int
    page: int
    page_size: int
