from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.agents.state import AgentState
from app.tools.analytics_tools import ToolName

AgentName=Literal['profit','advertising','inventory']
class RouteDecision(BaseModel):
    model_config=ConfigDict(extra='forbid')
    intent: Literal['profit','advertising','inventory','mixed','unsupported']
    selected_agents: list[AgentName]=Field(max_length=3)
    reason: str=Field(min_length=1,max_length=500)
    confidence: float | None=Field(default=None,ge=0,le=1)
    @model_validator(mode='after')
    def consistent(self):
        if len(set(self.selected_agents))!=len(self.selected_agents): raise ValueError('duplicate agents')
        if self.intent=='unsupported' and self.selected_agents: raise ValueError('unsupported has no agents')
        if self.intent=='mixed' and len(self.selected_agents)<2: raise ValueError('mixed requires multiple agents')
        if self.intent in ('profit','advertising','inventory') and self.selected_agents!=[self.intent]: raise ValueError('intent mismatch')
        return self

class Evidence(BaseModel):
    id: str
    agent: AgentName
    sku: str
    metric: str
    value: str | int | None
    unit: str
    source: str

class EvidenceSelection(BaseModel):
    model_config=ConfigDict(extra='forbid')
    evidence_ids: list[str]=Field(min_length=1,max_length=20)

class Report(BaseModel):
    problem_understanding: str
    key_findings: list[str]
    business_risks: list[str]
    suggested_actions: list[str]
    evidence_and_limits: list[str]
    evidence_ids: list[str]

class SupervisorState(AgentState):
    selected_tools: list[ToolName]=Field(default_factory=list)
    execution_status: Literal['pending','running','completed','failed','partial_failed','unsupported']='pending'
    route: RouteDecision | None=None
    evidence: dict[str,Evidence]=Field(default_factory=dict)
    expert_selections: dict[str,list[str]]=Field(default_factory=dict)
    report: Report | None=None
