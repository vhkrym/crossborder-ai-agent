from langgraph.graph import StateGraph, START, END
from app.agents.state import AgentState
from app.agents.nodes import execute_tools, summarize
from app.tools.analytics_tools import build_tools
from app.db.session import SessionLocal

def build_graph(session_factory=SessionLocal):
    tools=build_tools(session_factory)
    graph=StateGraph(AgentState)
    graph.add_node('execute_tools',lambda state:execute_tools(state,tools))
    graph.add_node('summarize',summarize)
    graph.add_edge(START,'execute_tools')
    graph.add_edge('execute_tools','summarize')
    graph.add_edge('summarize',END)
    return graph.compile()
