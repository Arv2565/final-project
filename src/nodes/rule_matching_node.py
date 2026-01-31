from typing import Dict, Any, List, Optional, TYPE_CHECKING

from langchain_core.runnables import RunnableConfig

from src.models import GraphState
from src.agents.activity_law.rule_matching import RuleMatchingAgent
from src.config.observability import get_langfuse_callback
from src.models.activity_law import ActivityLawState


# Lazy initialization
_rule_matching_agent = None
_callback_handler = None
_callbacks_initialized = False


<<<<<<< HEAD
def rule_matching_node(state: GraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
=======
def rule_matching_node(state: GraphState, config: RunnableConfig | None = None) -> Dict[str, Any]:
>>>>>>> 14a165ddc199668c3ad8563ab4d99d899b1c0e5e
    """LangGraph node that delegates to RuleMatchingAgent.
    
    This node breaks down statutes into logical rules (Premise-Conclusion).
    
    Args:
        state: GraphState
        config: Runtime configuration containing callbacks
        
    Returns:
        State update with 'activity_law_state.rule_matching'
    """
    global _rule_matching_agent
    
    if _rule_matching_agent is None:
        _rule_matching_agent = RuleMatchingAgent()
        
    callbacks = config.get("callbacks", []) if config else []
    result = _rule_matching_agent(state, callbacks=callbacks)
    
    # Update nested state
    current_activity_state = state.get("activity_law_state", ActivityLawState())
    if result and result.get("rule_matching"):
        current_activity_state.rule_matching = result["rule_matching"]
        
    return {**state, "activity_law_state": current_activity_state}
