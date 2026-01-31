from typing import Dict, Any, List
from src.models import GraphState, ProceduralGuidanceState
from src.models.procedural_guidance import EstimatedEffortOutput
from src.agents.agent_llm_helper import get_agent_llm
from src.prompts.procedural_prompts import ESTIMATED_EFFORT_SYSTEM_PROMPT


class EstimatedEffortAgent:
    """Provides effort estimates, costs, and final ordered procedural steps."""
    
    def __init__(self):
        self.llm = get_agent_llm(
            model_type="writer",
            output_schema=EstimatedEffortOutput,
        )
    
    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        """Generate final ordered steps with effort and cost estimates.
        
        Args:
            state: GraphState containing router_output and procedural_guidance_state
            callbacks: List of LangChain callbacks
            
        Returns:
            Dict with 'estimated_effort' field
        """
        print("\n💰 ESTIMATED EFFORT & COST AGENT")
        print("=" * 60)
        
        router_output = state.get("router_output")
        if not router_output:
            raise ValueError("Missing 'router_output' in state")
        
        cleaned_query = router_output.cleaned_query
        
        # Get all previous step outputs
        procedural_state = state.get("procedural_guidance_state", ProceduralGuidanceState())
        
        # Build context from all previous agents
        context_info = ""
        
        if procedural_state.timeline_constraints and procedural_state.timeline_constraints.constraints:
            context_info += "\n\nTimeline Constraints:\n"
            for constraint in procedural_state.timeline_constraints.constraints:
                context_info += f"- {constraint.description} ({constraint.time_limit})\n"
        
        if procedural_state.checklist and procedural_state.checklist.items:
            context_info += "\n\nChecklist Items:\n"
            for item in procedural_state.checklist.items:
                context_info += f"- [{item.priority.upper()}] {item.description}\n"
        
        if procedural_state.actor_mapping and procedural_state.actor_mapping.actor_mappings:
            context_info += "\n\nResponsible Actors:\n"
            for mapping in procedural_state.actor_mapping.actor_mappings:
                context_info += f"- {mapping.step}: {mapping.responsible_party}"
                if mapping.responsible_officer:
                    context_info += f" + {mapping.responsible_officer}"
                context_info += "\n"
        
        # Build user prompt
        user_prompt = f"""Query: {cleaned_query}
{context_info}

Synthesize all the above information to create:
1. Ordered procedural steps (step-by-step guide)
2. Time estimates for each step
3. Cost estimates for each step
4. Required documents for each step
5. Forms to fill (with generic references)
6. Contact points (where to go)
7. Overall timeline and cost summary

Be realistic about Indian judicial timelines. Account for typical delays.
Provide cost ranges, not fixed amounts.
Make this actionable and user-friendly."""
        
        try:
            output = self.llm.invoke(
                [
                    {"role": "system", "content": ESTIMATED_EFFORT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                config={"callbacks": callbacks}
            )
            
            print(f"✅ Generated {len(output.ordered_steps)} ordered steps")
            print(f"   Total time: {output.total_estimated_time}")
            print(f"   Total cost: {output.total_estimated_cost}")
            
            return {"estimated_effort": output}
            
        except Exception as e:
            print(f"⚠️  Effort estimation failed: {str(e)[:100]}")
            # Return a fallback object to prevent crash
            from src.models.procedural_guidance import StepEstimate
            
            fallback = EstimatedEffortOutput(
                ordered_steps=[
                    StepEstimate(
                        step_number=1,
                        description="Consult a lawyer (Automated fallback due to high system load).",
                        estimated_time="1-2 days",
                        estimated_cost="Consultation fees vary",
                        required_documents=[],
                        forms_to_fill=[],
                        contact_points=[]
                    )
                ],
                total_estimated_time="Unknown (System Load)",
                total_estimated_cost="Unknown"
            )
            return {"estimated_effort": fallback}
