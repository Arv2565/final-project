from typing import Dict, Any

from src.models import GraphState
from src.agents.intent_classifier_agent import IntentClassifierAgent


# Lazy initialization - agent is created on first call, not at module import
_intent_classifier_agent = None


def intent_classifier_node(state: GraphState) -> Dict[str, Any]:
    """LangGraph node that delegates to IntentClassifierAgent.
    
    This node classifies the user's intent and extracts legal entities
    from the cleaned query produced by QueryRouterAgent.
    
    Args:
        state: GraphState with 'router_output' field
        
    Returns:
        State update with 'classifier_output' field
    """
    global _intent_classifier_agent
    if _intent_classifier_agent is None:
        _intent_classifier_agent = IntentClassifierAgent()
    return _intent_classifier_agent(state)
