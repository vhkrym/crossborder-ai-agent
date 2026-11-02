"""Read-only deterministic tools; no provider or LLM required."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from langchain_core.tools import StructuredTool
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.db.session import SessionLocal
from app.services.analytics import analyze, AnalyticsNotFound
from app.schemas.analytics import AnalysisResponse

ToolName = Literal['analyze_profit','analyze_advertising','analyze_inventory']

class AnalysisInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    store_id: int = Field(gt=0)
    start_date: date
    end_date: date
    selected_sku: str | None = Field(default=None,min_length=1,max_length=100)
    window: int = Field(default=30,ge=1,le=365)
    safety_days: int = Field(default=7,ge=0,le=365)

    @model_validator(mode='after')
    def valid_range(self):
        if self.start_date>self.end_date: raise ValueError('invalid date range')
        if self.selected_sku is not None and not self.selected_sku.strip(): raise ValueError('blank SKU')
        return self

class ToolResult(BaseModel):
    tool: ToolName
    parameters: AnalysisInput
    status: Literal['success','warning','failed']
    data: AnalysisResponse | None = None
    conventions: str
    anomalies: list[str] = Field(default_factory=list)
    error: str | None = None

CONVENTIONS = {
    'analyze_profit': 'Refunds reduce revenue, not sold units; historical costs follow sale date. Nonpositive net revenue has null margin.',
    'analyze_advertising': 'Attributed sales are advertising-window sales, not store revenue. Zero denominators produce null; no CTR.',
    'analyze_inventory': 'Latest snapshot at or before cutoff; window ends on end_date. Inbound without ETA is not deducted; missing history yields null recommendations.'}

def execute_analysis(name: ToolName, parameters: AnalysisInput, session_factory=SessionLocal) -> ToolResult:
    if name not in CONVENTIONS: raise ValueError('unknown tool')
    parameters=AnalysisInput.model_validate(parameters)
    try:
        with session_factory() as session:
            # A private session with autoflush disabled; SQLite also enforces read-only SQL.
            session.autoflush=False
            connection=session.connection()
            if session.get_bind().dialect.name=='sqlite': connection.exec_driver_sql('PRAGMA query_only=ON')
            try:
                data=analyze(session,{'analyze_profit':'profit','analyze_advertising':'advertising','analyze_inventory':'inventory'}[name],parameters.store_id,parameters.start_date,parameters.end_date,parameters.selected_sku,parameters.window,parameters.safety_days)
            finally:
                # Restore on the SAME checked-out connection before rollback returns it.
                if session.get_bind().dialect.name=='sqlite': connection.exec_driver_sql('PRAGMA query_only=OFF')
                session.rollback()
        items=getattr(data,{'analyze_profit':'profit','analyze_advertising':'advertising','analyze_inventory':'inventory'}[name])
        anomalies=list(data.reasons)
        for row in items:
            anomalies.extend(f'{row.sku}:{reason}' for reason in row.reasons)
            if name=='analyze_inventory' and row.risk!='healthy': anomalies.append(f'{row.sku}:{row.risk}')
            if name=='analyze_profit' and row.contribution_profit is not None and row.contribution_profit<0: anomalies.append(f'{row.sku}:negative_profit')
            if name=='analyze_advertising' and row.acos is not None and row.acos>1: anomalies.append(f'{row.sku}:high_acos')
        return ToolResult(tool=name,parameters=parameters,status='warning' if anomalies else 'success',data=data,conventions=CONVENTIONS[name],anomalies=anomalies)
    except AnalyticsNotFound:
        error='store_or_sku_not_found'
    except SQLAlchemyError:
        error='database_error'
    return ToolResult(tool=name,parameters=parameters,status='failed',conventions=CONVENTIONS[name],error=error)


def build_tools(session_factory=SessionLocal):
    def bind(name):
        def run(**kwargs):
            return execute_analysis(name,AnalysisInput(**kwargs),session_factory).model_dump(mode='json')
        return StructuredTool.from_function(func=run,name=name,description=CONVENTIONS[name],args_schema=AnalysisInput)
    return {name:bind(name) for name in CONVENTIONS}
