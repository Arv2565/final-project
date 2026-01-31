from typing import Dict, Any, List, Optional, TYPE_CHECKING

from langchain_core.runnables import RunnableConfig

from src.models import GraphState
from src.agents.activity_law.response_generation import ResponseGenerationAgent
from src.config.observability import get_langfuse_callback

# Lazy initialization
_response_generation_agent = None
_callback_handler = None
_callbacks_initialized = False


<<<<<<< HEAD
def response_generation_node(state: GraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
=======
def response_generation_node(state: GraphState, config: RunnableConfig | None = None) -> Dict[str, Any]:
>>>>>>> 14a165ddc199668c3ad8563ab4d99d899b1c0e5e
    """LangGraph node that delegates to ResponseGenerationAgent.
    
    This node synthesizes the final response for the user.
    
    Args:
        state: GraphState
        config: Runtime configuration containing callbacks
        
    Returns:
        State update with 'final_response'
    """
    global _response_generation_agent
    global _callback_handler
    global _callbacks_initialized
    
    if _response_generation_agent is None:
        _response_generation_agent = ResponseGenerationAgent()
        
    if not _callbacks_initialized:
        _callback_handler = get_langfuse_callback()
        _callbacks_initialized = True
        
    callbacks = config.get("callbacks", []) if config else []
    result = _response_generation_agent(state, callbacks=callbacks)
    
    return {**state, **result}
