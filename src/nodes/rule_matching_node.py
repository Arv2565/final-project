from typing import Dict, Any, List

from src.models import GraphState
from src.agents.activity_law.rule_matching import RuleMatchingAgent
from src.config.observability import get_langfuse_callback
from src.models.activity_law import ActivityLawState


# Lazy initialization
_rule_matching_agent = None
_callback_handler = None
_callbacks_initialized = False


def rule_matching_node(state: GraphState) -> Dict[str, Any]:
    """LangGraph node that delegates to RuleMatchingAgent.
    
    This node breaks down statutes into logical rules (Premise-Conclusion).
    
    Args:
        state: GraphState
        
    Returns:
        State update with 'activity_law_state.rule_matching'
    """
    global _rule_matching_agent
    global _callback_handler
    global _callbacks_initialized
    
    if _rule_matching_agent is None:
        _rule_matching_agent = RuleMatchingAgent()
        
    if not _callbacks_initialized:
        _callback_handler = get_langfuse_callback()
        _callbacks_initialized = True
        
    callbacks = [_callback_handler] if _callback_handler else []
    result = _rule_matching_agent(state, callbacks=callbacks)
    
    # Update nested state
    current_activity_state = state.get("activity_law_state", ActivityLawState())
    if result and result.get("rule_matching"):
        current_activity_state.rule_matching = result["rule_matching"]
        
    return {"activity_law_state": current_activity_state}
