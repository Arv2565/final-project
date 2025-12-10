from typing import Dict, Any

from src.models import GraphState
from src.agents.intent_classifier_agent import IntentClassifierAgent
from src.config.observability import get_langfuse_callback


# Lazy initialization - agent is created on first call, not at module import
_intent_classifier_agent = None
_callback_handler = None
_callbacks_initialized = False


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
    global _callback_handler
    global _callbacks_initialized

    if _intent_classifier_agent is None:
        _intent_classifier_agent = IntentClassifierAgent()

    if not _callbacks_initialized:
        _callback_handler = get_langfuse_callback()
        _callbacks_initialized = True

    callbacks = [_callback_handler] if _callback_handler else []
    return _intent_classifier_agent(state, callbacks=callbacks)
