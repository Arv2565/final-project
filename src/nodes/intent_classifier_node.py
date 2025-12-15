from typing import Dict, Any

from src.models import GraphState
from src.agents.intent_classifier_agent import IntentClassifierAgent
from src.config.observability import get_langfuse_callback


# Lazy initialization - agent is created on first call, not at module import
_intent_classifier_agent = None
_callback_handler = None
_callbacks_initialized = False


def intent_classifier_node(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """LangGraph node that delegates to IntentClassifierAgent.
    
    This node classifies the user's intent and extracts legal entities
    from the cleaned query produced by QueryRouterAgent.
    
    Args:
        state: GraphState with 'router_output' field
        config: Runtime configuration containing callbacks
        
    Returns:
        State update with 'classifier_output' field
    """
    global _intent_classifier_agent

    if _intent_classifier_agent is None:
        _intent_classifier_agent = IntentClassifierAgent()

    callbacks = config.get("callbacks", []) if config else []
    result = _intent_classifier_agent(state, callbacks=callbacks)
    return {**state, **result}
