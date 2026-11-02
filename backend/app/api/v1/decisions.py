from uuid import UUID
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Query
from app.services.decisions import DecisionService
from app.schemas.decisions import GenerateRequest,GenerateResponse,Proposal,ProposalPage,ProposalType
router=APIRouter(prefix='/decisions',tags=['local-demo-decisions'])
def get_decision_service():return DecisionService()
@router.post('/generate',response_model=GenerateResponse)
def generate(body:GenerateRequest,service=Depends(get_decision_service)):
    try:return service.generate(body.source_task_id)
    except LookupError as e:raise HTTPException(404,str(e)) from e
    except ValueError as e:raise HTTPException(409,'untrusted_or_incomplete_source_task') from e
@router.get('',response_model=ProposalPage)
def listing(store_id:int=Query(gt=0),proposal_type:ProposalType|None=None,status:Literal['draft','pending_review','approved','rejected']|None=None,risk_level:Literal['high','medium','low']|None=None,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),service=Depends(get_decision_service)):
    return service.list(store_id,proposal_type,status,risk_level,page,page_size)
@router.get('/{proposal_id}',response_model=Proposal)
def detail(proposal_id:str,service=Depends(get_decision_service)):
    try:return service.get(UUID(proposal_id))
    except (ValueError,LookupError) as e:raise HTTPException(404,'proposal_not_found') from e
