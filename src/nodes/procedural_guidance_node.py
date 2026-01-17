from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from src.models import GraphState
from src.workflows.procedural.builder import build_procedural_graph

def procedural_guidance_node(state: GraphState, config: RunnableConfig | None = None) -> Dict[str, Any]:
    """Node wrapper for Procedural Guidance workflow.
    
    Args:
        state: GraphState containing router_output
        config: Runtime configuration containing callbacks
        
    Returns:
        Dict with procedural_guidance_state
    """
    procedural_graph = build_procedural_graph()
    # Invoke the subgraph with the current state and config
    return procedural_graph.invoke(state, config=config)

