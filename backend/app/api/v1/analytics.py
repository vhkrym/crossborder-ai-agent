from datetime import date
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.analytics import AnalysisResponse
from app.services.analytics import analyze, AnalyticsNotFound

router=APIRouter(tags=['analytics'])

def parameters(store_id: Annotated[int, Query(gt=0)],start_date: date,end_date: date,sku: Annotated[str | None, Query(min_length=1)]=None,window: Annotated[int,Query(ge=1,le=365)]=30,safety_days: Annotated[int,Query(ge=0,le=365)]=7,sort_by: Literal['contribution_profit','net_revenue','profit_margin']='contribution_profit',descending: bool=True):
    if start_date>end_date: raise HTTPException(422,'start_date must not exceed end_date')
    return dict(store_id=store_id,start=start_date,end=end_date,sku=sku,window=window,safety_days=safety_days,sort_by=sort_by,descending=descending)

def endpoint(kind):
    def handle(params=Depends(parameters),session: Session=Depends(get_db)):
        try: return analyze(session,kind,**params)
        except AnalyticsNotFound as exc: raise HTTPException(404,str(exc)) from exc
        except ValueError as exc: raise HTTPException(422,str(exc)) from exc
    return handle

for path,kind in [('/dashboard/overview','overview'),('/analytics/profit','profit'),('/analytics/advertising','advertising'),('/analytics/inventory-risk','inventory')]:
    router.add_api_route(path,endpoint(kind),methods=['GET'],response_model=AnalysisResponse,name=kind)
