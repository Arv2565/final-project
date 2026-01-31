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


<<<<<<< HEAD
def fact_structuring_node(state: GraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
=======
def fact_structuring_node(state: GraphState, config: RunnableConfig | None = None) -> Dict[str, Any]:
>>>>>>> 14a165ddc199668c3ad8563ab4d99d899b1c0e5e
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
<<<<<<< HEAD
        
    return {**state, "activity_law_state": current_activity_state}
=======
    
    # We want to keep other keys returned by agent (like pending_clarification, clarification_counts)
    # But we don't want to duplicate fact_structuring in the top level if it's not needed (it's not needed by GraphState at top level, only in activity_law_state really, but let's follow existing pattern).
    # actually, GraphState doesn't have 'fact_structuring' at top level.
    
    output = {**state, "activity_law_state": current_activity_state}
    
    # Merge other result keys (pending_clarification, clarification_counts)
    if result:
         for k, v in result.items():
            if k != "fact_structuring":
                output[k] = v
                
    return output
>>>>>>> 14a165ddc199668c3ad8563ab4d99d899b1c0e5e
