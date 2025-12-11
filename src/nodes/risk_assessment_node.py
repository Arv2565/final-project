from typing import Dict, Any, List

from src.models import GraphState
from src.agents.activity_law.risk_assessment import RiskAssessmentAgent
from src.config.observability import get_langfuse_callback
from src.models.activity_law import ActivityLawState


# Lazy initialization
_risk_assessment_agent = None
_callback_handler = None
_callbacks_initialized = False


def risk_assessment_node(state: GraphState) -> Dict[str, Any]:
    """LangGraph node that delegates to RiskAssessmentAgent.
    
    This node evaluates the risk level of the activity against the matched rules.
    
    Args:
        state: GraphState
        
    Returns:
        State update with 'activity_law_state.risk_assessment'
    """
    global _risk_assessment_agent
    global _callback_handler
    global _callbacks_initialized
    
    if _risk_assessment_agent is None:
        _risk_assessment_agent = RiskAssessmentAgent()
        
    if not _callbacks_initialized:
        _callback_handler = get_langfuse_callback()
        _callbacks_initialized = True
        
    callbacks = [_callback_handler] if _callback_handler else []
    result = _risk_assessment_agent(state, callbacks=callbacks)
    
    # Update nested state
    current_activity_state = state.get("activity_law_state", ActivityLawState())
    if result and result.get("risk_assessment"):
        current_activity_state.risk_assessment = result["risk_assessment"]
        
    return {"activity_law_state": current_activity_state}
