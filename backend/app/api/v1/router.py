from fastapi import APIRouter
from app.schemas.health import HealthResponse

router = APIRouter()

@router.get('/health', response_model=HealthResponse, tags=['health'])
def health() -> HealthResponse:
    return HealthResponse()

from app.api.v1.analytics import router as analytics_router
router.include_router(analytics_router)

from pydantic import BaseModel
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Store

class StoreResponse(BaseModel):
    id: int
    name: str
    marketplace: str
    market: str
    currency: str

@router.get('/stores', response_model=list[StoreResponse], tags=['stores'])
def list_stores(session: Session = Depends(get_db)):
    return [StoreResponse(id=s.id,name=s.name,marketplace=s.marketplace,market=s.market,currency=s.currency) for s in session.scalars(select(Store).order_by(Store.id))]

from app.api.v1.agent_tasks import router as task_router
router.include_router(task_router)

from app.api.v1.decisions import router as decisions_router
router.include_router(decisions_router)

from app.api.v1.decision_approvals import router as approvals_router
router.include_router(approvals_router)

from app.api.v1.simulations import router as simulations_router
router.include_router(simulations_router)
