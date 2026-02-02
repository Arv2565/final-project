from typing import Dict, Any, List, Optional, TYPE_CHECKING

from langchain_core.runnables import RunnableConfig

from src.models import GraphState
from src.agents.query_router_agent import QueryRouterAgent
from src.config.observability import get_langfuse_callback


# Lazy initialization - agent is created on first call, not at module import
_query_router_agent = None
_callback_handler = None
_callbacks_initialized = False


def query_router_node(state: GraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """LangGraph node that delegates to QueryRouterAgent.
    
    This node is the entry point of the legal query processing pipeline.
    It normalizes the user query, translates to English if needed, and
    extracts basic metadata.
    
    Args:
        state: GraphState with 'user_query' field
        config: Runtime configuration containing callbacks
        
    Returns:
        State update with 'router_output' field
    """
    # Skip if we already have router output (resuming after clarification)
    if state.get("router_output"):
        return {}
        
    global _query_router_agent
    
    if _query_router_agent is None:
        _query_router_agent = QueryRouterAgent()
        
    callbacks = config.get("callbacks", []) if config else []
    result = _query_router_agent(state, callbacks=callbacks)
    return {**state, **result}
