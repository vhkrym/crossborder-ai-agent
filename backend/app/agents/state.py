from typing import Literal
from pydantic import Field
from app.tools.analytics_tools import AnalysisInput, ToolName, ToolResult
from app.agents.trace import ExecutionTrace

class AgentState(AnalysisInput):
    task_id: str = Field(min_length=1,max_length=100)
    user_query: str = Field(min_length=1,max_length=4000)
    intent: str = 'explicit_tools'
    selected_tools: list[ToolName] = Field(min_length=1,max_length=3)
    tool_results: dict[str,ToolResult] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    execution_status: Literal['pending','running','completed','failed'] = 'pending'
    final_answer: str | None = None
    traces: list[ExecutionTrace] = Field(default_factory=list)
    schema_version: str = '1'
