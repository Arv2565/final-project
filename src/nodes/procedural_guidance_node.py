from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from src.models import GraphState
from src.workflows.procedural.builder import build_procedural_graph

def procedural_guidance_node(state: GraphState, config: RunnableConfig | None = None) -> Dict[str, Any]:
    """Legacy/Criminal Procedural Guidance Node."""
    return criminal_procedural_guidance_node(state, config)

def civil_procedural_guidance_node(state: GraphState, config: RunnableConfig | None = None) -> Dict[str, Any]:
    """Node wrapper for Civil Procedural Guidance workflow."""
    # Inject civil domain
    input_state = state.copy()
    input_state["active_legal_domain"] = "civil"
    
    procedural_graph = build_procedural_graph()
    result = procedural_graph.invoke(input_state, config=config)
    
    output = {}
    if "procedural_guidance_state" in result:
        output["procedural_guidance_civil_state"] = result["procedural_guidance_state"]
    
    # Propagate clarification requests
    if "pending_clarification" in result:
        output["pending_clarification"] = result["pending_clarification"]
    
    if "clarification_counts" in result:
        output["clarification_counts"] = result["clarification_counts"]
        
    return output

def criminal_procedural_guidance_node(state: GraphState, config: RunnableConfig | None = None) -> Dict[str, Any]:
    """Node wrapper for Criminal Procedural Guidance workflow."""
    # Inject criminal domain
    input_state = state.copy()
    input_state["active_legal_domain"] = "criminal"
    
    procedural_graph = build_procedural_graph()
    result = procedural_graph.invoke(input_state, config=config)
    
    output = {}
    if "procedural_guidance_state" in result:
        output["procedural_guidance_criminal_state"] = result["procedural_guidance_state"]
        # Also populate legacy field for compatibility
        output["procedural_guidance_state"] = result["procedural_guidance_state"]
    
    # Propagate clarification requests
    if "pending_clarification" in result:
        output["pending_clarification"] = result["pending_clarification"]
    
    if "clarification_counts" in result:
        output["clarification_counts"] = result["clarification_counts"]
        
    return output
