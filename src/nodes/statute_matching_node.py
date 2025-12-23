from typing import Dict, Any, List, Optional, TYPE_CHECKING

from langchain_core.runnables import RunnableConfig

from src.models import GraphState
from src.agents.activity_law.statute_matching import StatuteMatchingAgent
from src.config.observability import get_langfuse_callback
from src.models.activity_law import ActivityLawState


# Lazy initialization
_statute_matching_agent = None
_callback_handler = None
_callbacks_initialized = False


def statute_matching_node(state: GraphState, config: RunnableConfig | None = None) -> Dict[str, Any]:
    """LangGraph node that delegates to StatuteMatchingAgent.
    
    This node identifies relevant statutes for the structured facts.
    
    Args:
        state: GraphState
        config: Runtime configuration containing callbacks
        
    Returns:
        State update with 'activity_law_state.statute_matching'
    """
    global _statute_matching_agent
    
    if _statute_matching_agent is None:
        _statute_matching_agent = StatuteMatchingAgent()
        
    callbacks = config.get("callbacks", []) if config else []
    result = _statute_matching_agent(state, callbacks=callbacks)
    
    # Update nested state
    current_activity_state = state.get("activity_law_state", ActivityLawState())
    if result and result.get("statute_matching"):
        current_activity_state.statute_matching = result["statute_matching"]
        
    return {**state, "activity_law_state": current_activity_state}
