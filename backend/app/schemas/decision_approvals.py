from datetime import datetime
from uuid import UUID
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
from app.schemas.decisions import Proposal

class ReviewRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    comment: str=Field(default='',max_length=2000)
class Audit(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    audit_id: UUID
    proposal_id: UUID
    store_id: int
    action: Literal['submit','approve','reject']
    from_status: Literal['draft','pending_review']
    to_status: Literal['pending_review','approved','rejected']
    reviewer_id: str
    identity_source: str
    comment: str
    created_at: datetime
class ReviewResponse(BaseModel):
    proposal: Proposal
    audit: Audit
