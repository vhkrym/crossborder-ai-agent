from datetime import datetime
from typing import Literal
from pydantic import BaseModel
from app.tools.analytics_tools import AnalysisInput, ToolName

class ExecutionTrace(BaseModel):
    node: str
    tool: ToolName | None = None
    parameters: AnalysisInput | None = None
    status: Literal['success','warning','failed']
    started_at: datetime
    ended_at: datetime
    error: str | None = None
    summary: str
