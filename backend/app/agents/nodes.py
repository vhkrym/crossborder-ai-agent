from datetime import datetime, timezone
from app.agents.state import AgentState
from app.agents.trace import ExecutionTrace
from app.tools.analytics_tools import AnalysisInput, ToolResult

def execute_tools(state: AgentState, tools):
    params=AnalysisInput.model_validate({k:getattr(state,k) for k in AnalysisInput.model_fields})
    results={};errors=[];traces=[]
    for name in dict.fromkeys(state.selected_tools):
        started=datetime.now(timezone.utc)
        try:
            result=ToolResult.model_validate(tools[name].invoke(params.model_dump()))
        except Exception:
            # Never persist raw exception text, SQL, credentials, or user query in traces.
            result=ToolResult(tool=name,parameters=params,status='failed',conventions='Tool execution failed',error='tool_execution_error')
        results[name]=result
        if result.status=='failed':errors.append(f'{name}:{result.error}')
        traces.append(ExecutionTrace(node='execute_tools',tool=name,parameters=params,status=result.status,started_at=started,ended_at=datetime.now(timezone.utc),error=result.error,summary=f'{len(result.anomalies)} anomalies; data present: {result.data is not None}'))
    return dict(tool_results=results,errors=errors,traces=traces,execution_status='running',final_answer=None)

def summarize(state: AgentState):
    started=datetime.now(timezone.utc);failed=bool(state.errors)
    warnings=sum(r.status=='warning' for r in state.tool_results.values())
    return dict(execution_status='failed' if failed else 'completed',final_answer=f'Execution failed: {len(state.errors)} tool errors.' if failed else f'Completed {len(state.tool_results)} tools; {warnings} contain data warnings. See structured results.',traces=state.traces+[ExecutionTrace(node='summarize',status='failed' if failed else 'success',started_at=started,ended_at=datetime.now(timezone.utc),summary='Failed task' if failed else 'Structured results ready')])
