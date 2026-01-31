from typing import Dict, Any, Optional
from langchain_core.runnables import RunnableConfig
from src.models import GraphState
from src.agents.placeholders import ProceduralGuidanceAgent


def procedural_guidance_node(state: GraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Node wrapper for Procedural Guidance workflow.
    
    Args:
        state: GraphState containing router_output
        config: Runtime configuration containing callbacks
        
    Returns:
        Dict with procedural_guidance_state
    """
    callbacks = config.get("callbacks", []) if config else []
    agent = ProceduralGuidanceAgent()
    return agent(state, callbacks=callbacks)

