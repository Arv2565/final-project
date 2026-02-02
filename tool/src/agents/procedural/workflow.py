from typing import Dict, Any, List
from src.config.observability import get_langfuse_callback
from src.models import GraphState, ProceduralGuidanceState
from src.agents.procedural.timeline_constraint import TimelineConstraintAgent
from src.agents.procedural.checklist_generator import ChecklistGeneratorAgent
from src.agents.procedural.responsible_actor_mapper import ResponsibleActorMapperAgent
from src.agents.procedural.estimated_effort import EstimatedEffortAgent
from src.agents.procedural.response_generation import ProceduralResponseGenerationAgent


class ProceduralGuidanceWorkflow:
    """Orchestrates the 5-step Procedural Guidance workflow."""
    
    def __init__(self):
        self.timeline_constraint_agent = TimelineConstraintAgent()
        self.checklist_generator_agent = ChecklistGeneratorAgent()
        self.responsible_actor_mapper_agent = ResponsibleActorMapperAgent()
        self.estimated_effort_agent = EstimatedEffortAgent()
        self.response_generation_agent = ProceduralResponseGenerationAgent()
        self.callback_handler = get_langfuse_callback()
    
    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        """Execute the workflow sequence.
        
        Args:
            state: GraphState
            callbacks: List of LangChain callbacks (for trace propagation)
            
        Returns:
            Dict with 'procedural_guidance_state' and 'final_response' fields
        """
        print("\n" + "="*80)
        print("🔄 STARTING PROCEDURAL GUIDANCE WORKFLOW")
        print("="*80)
        
        # Use passed callbacks if available, otherwise fallback to internal handler
        active_callbacks = callbacks if callbacks else ([self.callback_handler] if self.callback_handler else [])
        
        # Initialize Accumulator State
        current_state = state.get("procedural_guidance_state", ProceduralGuidanceState())
        
        # Step 1: Timeline/Constraint Identifier
        timeline_result = self.timeline_constraint_agent(state, callbacks=active_callbacks)
        if timeline_result and timeline_result.get("timeline_constraints"):
            current_state.timeline_constraints = timeline_result["timeline_constraints"]
        
        # Update state for next step
        state["procedural_guidance_state"] = current_state
        
        # Step 2: Checklist Generator
        checklist_result = self.checklist_generator_agent(state, callbacks=active_callbacks)
        if checklist_result and checklist_result.get("checklist"):
            current_state.checklist = checklist_result["checklist"]
        
        state["procedural_guidance_state"] = current_state
        
        # Step 3: Responsible Actor Mapper
        actor_result = self.responsible_actor_mapper_agent(state, callbacks=active_callbacks)
        if actor_result and actor_result.get("actor_mapping"):
            current_state.actor_mapping = actor_result["actor_mapping"]
        
        state["procedural_guidance_state"] = current_state
        
        # Step 4: Estimated Effort & Cost
        effort_result = self.estimated_effort_agent(state, callbacks=active_callbacks)
        if effort_result and effort_result.get("estimated_effort"):
            current_state.estimated_effort = effort_result["estimated_effort"]
        
        state["procedural_guidance_state"] = current_state
        
        # Step 5: Response Generation (Final Synthesis)
        response_result = self.response_generation_agent(state, callbacks=active_callbacks)
        final_response = response_result.get("final_response", "")
        
        # Generate summary for legacy field compatibility
        procedural_summary = ""
        if current_state.estimated_effort and current_state.estimated_effort.ordered_steps:
            procedural_summary = f"Procedural Steps ({len(current_state.estimated_effort.ordered_steps)} steps):\n"
            for step in current_state.estimated_effort.ordered_steps[:3]:  # First 3 steps
                procedural_summary += f"{step.step_number}. {step.action}\n"
            procedural_summary += f"\nTotal Time: {current_state.estimated_effort.total_estimated_time}"
            procedural_summary += f"\nTotal Cost: {current_state.estimated_effort.total_estimated_cost}"
        
        print("\n" + "="*80)
        print("✅ PROCEDURAL GUIDANCE WORKFLOW COMPLETED")
        print("="*80)
        
        return {
            "procedural_guidance_state": current_state,
            "procedural_advice": procedural_summary,  # Legacy field
            "final_response": final_response  # New comprehensive response
        }

