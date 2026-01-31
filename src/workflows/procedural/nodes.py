from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from src.models import GraphState, ProceduralGuidanceState

# Import Agents
from src.agents.procedural.timeline_constraint import TimelineConstraintAgent
from src.agents.procedural.checklist_generator import ChecklistGeneratorAgent
from src.agents.procedural.responsible_actor_mapper import ResponsibleActorMapperAgent
from src.agents.procedural.estimated_effort import EstimatedEffortAgent
from src.agents.procedural.response_generation import ProceduralResponseGenerationAgent

def get_procedural_state(state: GraphState) -> ProceduralGuidanceState:
    """Helper to extract or initialize procedural state."""
    return state.get("procedural_guidance_state", ProceduralGuidanceState())

def timeline_constraint_node(state: GraphState, config: RunnableConfig | None = None) -> Dict[str, Any]:
    """Node for identifying timeline constraints."""
    callbacks = config.get("callbacks", []) if config else []
    agent = TimelineConstraintAgent()
    
    current_state = get_procedural_state(state)
    result = agent(state, callbacks=callbacks)
    
    if result and result.get("timeline_constraints"):
        current_state.timeline_constraints = result["timeline_constraints"]
        
    output = {"procedural_guidance_state": current_state}
    
    # Merge other result keys (pending_clarification, clarification_counts)
    if result:
         for k, v in result.items():
            if k != "timeline_constraints":
                output[k] = v
                
    return output

def checklist_generator_node(state: GraphState, config: RunnableConfig | None = None) -> Dict[str, Any]:
    """Node for generating procedural checklist."""
    callbacks = config.get("callbacks", []) if config else []
    agent = ChecklistGeneratorAgent()
    
    current_state = get_procedural_state(state)
    result = agent(state, callbacks=callbacks)
    
    if result and result.get("checklist"):
        current_state.checklist = result["checklist"]
        
    return {"procedural_guidance_state": current_state}

def responsible_actor_node(state: GraphState, config: RunnableConfig | None = None) -> Dict[str, Any]:
    """Node for mapping responsible actors."""
    callbacks = config.get("callbacks", []) if config else []
    agent = ResponsibleActorMapperAgent()
    
    current_state = get_procedural_state(state)
    result = agent(state, callbacks=callbacks)
    
    if result and result.get("actor_mapping"):
        current_state.actor_mapping = result["actor_mapping"]
        
    return {"procedural_guidance_state": current_state}

def estimated_effort_node(state: GraphState, config: RunnableConfig | None = None) -> Dict[str, Any]:
    """Node for estimating effort and cost."""
    callbacks = config.get("callbacks", []) if config else []
    agent = EstimatedEffortAgent()
    
    current_state = get_procedural_state(state)
    result = agent(state, callbacks=callbacks)
    
    if result and result.get("estimated_effort"):
        current_state.estimated_effort = result["estimated_effort"]
        
    return {"procedural_guidance_state": current_state}

def procedural_response_node(state: GraphState, config: RunnableConfig | None = None) -> Dict[str, Any]:
    """Node for generating final procedural response."""
    callbacks = config.get("callbacks", []) if config else []
    agent = ProceduralResponseGenerationAgent()
    
    current_state = get_procedural_state(state)
    result = agent(state, callbacks=callbacks)
    
    final_response = result.get("final_response", "")
    
    # Generate summary for legacy field compatibility
    procedural_summary = ""
    if current_state.estimated_effort and current_state.estimated_effort.ordered_steps:
        procedural_summary = f"Procedural Steps ({len(current_state.estimated_effort.ordered_steps)} steps):\n"
        for step in current_state.estimated_effort.ordered_steps[:3]:  # First 3 steps
            procedural_summary += f"{step.step_number}. {step.action}\n"
        procedural_summary += f"\nTotal Time: {current_state.estimated_effort.total_estimated_time}"
        procedural_summary += f"\nTotal Cost: {current_state.estimated_effort.total_estimated_cost}"
    
    return {
        "procedural_guidance_state": current_state,
        "procedural_advice": procedural_summary,
        "final_response": final_response
    }
