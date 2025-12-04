from typing import Dict, Any

from src.models import GraphState
from src.agents.query_router_agent import QueryRouterAgent


# Lazy initialization - agent is created on first call, not at module import
_query_router_agent = None


def query_router_node(state: GraphState) -> Dict[str, Any]:
    """LangGraph node that delegates to QueryRouterAgent.
    
    This node is the entry point of the legal query processing pipeline.
    It normalizes the user query, translates to English if needed, and
    extracts basic metadata.
    
    Args:
        state: GraphState with 'user_query' field
        
    Returns:
        State update with 'router_output' field
    """
    global _query_router_agent
    if _query_router_agent is None:
        _query_router_agent = QueryRouterAgent()
    return _query_router_agent(state)
