from typing import Dict, Any, List

from src.models import GraphState
from src.agents.query_router_agent import QueryRouterAgent
from src.config.observability import get_langfuse_callback


# Lazy initialization - agent is created on first call, not at module import
_query_router_agent = None
_callback_handler = None
_callbacks_initialized = False


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
    global _callback_handler
    global _callbacks_initialized
    
    if _query_router_agent is None:
        _query_router_agent = QueryRouterAgent()
        
    if not _callbacks_initialized:
        _callback_handler = get_langfuse_callback()
        _callbacks_initialized = True
        
    callbacks = [_callback_handler] if _callback_handler else []
    return _query_router_agent(state, callbacks=callbacks)
