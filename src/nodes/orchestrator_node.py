from typing import Dict, Any, List

from src.models import GraphState
from src.agents.orchestrator_agent import OrchestratorAgent
from src.config.observability import get_langfuse_callback


# Lazy initialization
_orchestrator_agent = None
_callback_handler = None
_callbacks_initialized = False


def orchestrator_node(state: GraphState) -> Dict[str, Any]:
    """LangGraph node that delegates to OrchestratorAgent.
    
    This node serves as the central brain, deciding the next steps in the workflow
    based on the intent and entities.
    
    Args:
        state: GraphState with 'router_output' and 'classifier_output'
        
    Returns:
        State update with 'orchestrator_plan' field
    """
    global _orchestrator_agent
    global _callback_handler
    global _callbacks_initialized
    
    if _orchestrator_agent is None:
        _orchestrator_agent = OrchestratorAgent()
        
    if not _callbacks_initialized:
        _callback_handler = get_langfuse_callback()
        _callbacks_initialized = True
        
    callbacks = [_callback_handler] if _callback_handler else []
    return _orchestrator_agent(state, callbacks=callbacks)
