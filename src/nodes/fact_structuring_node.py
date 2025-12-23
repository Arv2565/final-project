from typing import Dict, Any, List, Optional, TYPE_CHECKING

from langchain_core.runnables import RunnableConfig

from src.models import GraphState
from src.agents.activity_law.fact_structuring import FactStructuringAgent
from src.config.observability import get_langfuse_callback
from src.models.activity_law import ActivityLawState


# Lazy initialization
_fact_structuring_agent = None
_callback_handler = None
_callbacks_initialized = False


def fact_structuring_node(state: GraphState, config: RunnableConfig | None = None) -> Dict[str, Any]:
    """LangGraph node that delegates to FactStructuringAgent.
    
    This node structures the raw query into a canonical fact pattern.
    
    Args:
        state: GraphState
        config: Runtime configuration containing callbacks
        
    Returns:
        State update with 'activity_law_state.fact_structuring'
    """
    global _fact_structuring_agent
    
    if _fact_structuring_agent is None:
        _fact_structuring_agent = FactStructuringAgent()
        
    callbacks = config.get("callbacks", []) if config else []
    result = _fact_structuring_agent(state, callbacks=callbacks)
    
    # Update nested state
    current_activity_state = state.get("activity_law_state", ActivityLawState())
    if result and result.get("fact_structuring"):
        current_activity_state.fact_structuring = result["fact_structuring"]
        
    return {**state, "activity_law_state": current_activity_state}
