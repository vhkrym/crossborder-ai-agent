from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,Query
from app.schemas.simulations import EmptySimulationRequest,SimulationCreated,SimulationDetail,SimulationPage,SimulationStatus
from app.schemas.decisions import ProposalType
from app.services.simulations import SimulationService
router=APIRouter(tags=['local-demo-simulation-only'])
def get_simulation_service():return SimulationService()
@router.post('/decisions/{proposal_id}/simulate',response_model=SimulationCreated)
def create(proposal_id:str,body:EmptySimulationRequest,service=Depends(get_simulation_service)):
    try:id=UUID(proposal_id)
    except ValueError as e:raise HTTPException(404,'proposal_not_found') from e
    try:return service.create(id)
    except LookupError as e:raise HTTPException(404,str(e)) from e
    except ValueError as e:raise HTTPException(409,'approved_proposal_with_audit_required') from e
@router.get('/simulations',response_model=SimulationPage)
def listing(store_id:int=Query(gt=0),status:SimulationStatus|None=None,proposal_type:ProposalType|None=None,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),service=Depends(get_simulation_service)):
    return service.list(store_id,status,proposal_type,page,page_size)
@router.get('/simulations/{simulation_id}',response_model=SimulationDetail)
def detail(simulation_id:str,service=Depends(get_simulation_service)):
    try:return service.get(UUID(simulation_id))
    except (ValueError,LookupError) as e:raise HTTPException(404,'simulation_not_found') from e
