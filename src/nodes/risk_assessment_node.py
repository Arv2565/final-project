from typing import Dict, Any, List, Optional, TYPE_CHECKING

from langchain_core.runnables import RunnableConfig

from src.models import GraphState
from src.agents.activity_law.risk_assessment import RiskAssessmentAgent
from src.config.observability import get_langfuse_callback
from src.models.activity_law import ActivityLawState


# Lazy initialization
_risk_assessment_agent = None
_callback_handler = None
_callbacks_initialized = False


<<<<<<< HEAD
def risk_assessment_node(state: GraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
=======
def risk_assessment_node(state: GraphState, config: RunnableConfig | None = None) -> Dict[str, Any]:
>>>>>>> 14a165ddc199668c3ad8563ab4d99d899b1c0e5e
    """LangGraph node that delegates to RiskAssessmentAgent.
    
    This node evaluates the risk level of the activity against the matched rules.
    
    Args:
        state: GraphState
        config: Runtime configuration containing callbacks
        
    Returns:
        State update with 'activity_law_state.risk_assessment'
    """
    global _risk_assessment_agent
    
    if _risk_assessment_agent is None:
        _risk_assessment_agent = RiskAssessmentAgent()
        
    callbacks = config.get("callbacks", []) if config else []
    result = _risk_assessment_agent(state, callbacks=callbacks)
    
    # Update nested state
    current_activity_state = state.get("activity_law_state", ActivityLawState())
    if result and result.get("risk_assessment"):
        current_activity_state.risk_assessment = result["risk_assessment"]
        
    return {**state, "activity_law_state": current_activity_state}
