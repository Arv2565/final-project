from typing import Dict, Any, List, Optional, TYPE_CHECKING

from langchain_core.runnables import RunnableConfig

from src.models import GraphState
from src.agents.orchestrator_agent import OrchestratorAgent
from src.config.observability import get_langfuse_callback


# Lazy initialization
_orchestrator_agent = None
_callback_handler = None
_callbacks_initialized = False


def orchestrator_node(state: GraphState, config: RunnableConfig | None = None) -> Dict[str, Any]:
    """LangGraph node that delegates to OrchestratorAgent.
    
    This node serves as the central brain, deciding the next steps in the workflow
    based on the intent and entities.
    
    Args:
        state: GraphState with 'router_output'
        config: Runtime configuration containing callbacks
        
    Returns:
        State update with 'orchestrator_plan' field
    """
    global _orchestrator_agent
    
    if _orchestrator_agent is None:
        _orchestrator_agent = OrchestratorAgent()
        
    callbacks = config.get("callbacks", []) if config else []
    result = _orchestrator_agent(state, callbacks=callbacks)
    return {**state, **result}
