from typing import Dict, Any, List
from src.models import GraphState, ProceduralGuidanceState
from src.models.procedural_guidance import ChecklistOutput
from src.agents.agent_llm_helper import get_agent_llm
from src.prompts.procedural_prompts import CHECKLIST_GENERATOR_SYSTEM_PROMPT
<<<<<<< HEAD
=======
from src.prompts.procedural_civil_prompts import CIVIL_CHECKLIST_GENERATOR_SYSTEM_PROMPT
>>>>>>> 14a165ddc199668c3ad8563ab4d99d899b1c0e5e


class ChecklistGeneratorAgent:
    """Generates prioritized checklist of documents and items to prepare."""
    
    def __init__(self):
        self.llm = get_agent_llm(
            model_type="writer",
            output_schema=ChecklistOutput,
        )
    
    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        """Generate prioritized preparation checklist.
        
        Args:
            state: GraphState containing router_output and procedural_guidance_state
            callbacks: List of LangChain callbacks
            
        Returns:
            Dict with 'checklist' field
        """
        print("\n📋 CHECKLIST GENERATOR AGENT")
        print("=" * 60)
        
        router_output = state.get("router_output")
<<<<<<< HEAD
=======
        active_domain = state.get("active_legal_domain", "criminal")
        
>>>>>>> 14a165ddc199668c3ad8563ab4d99d899b1c0e5e
        if not router_output:
            raise ValueError("Missing 'router_output' in state")
        
        cleaned_query = router_output.cleaned_query
        
        # Get timeline constraints from previous step
        procedural_state = state.get("procedural_guidance_state", ProceduralGuidanceState())
        timeline_info = ""
        if procedural_state.timeline_constraints:
            timeline_info = "\n\nTimeline Constraints Identified:\n"
            for constraint in procedural_state.timeline_constraints.constraints:
                timeline_info += f"- {constraint.description} ({constraint.time_limit})\n"
        
        # Build user prompt
        user_prompt = f"""Query: {cleaned_query}
{timeline_info}

Generate a prioritized checklist of documents and items to prepare for this procedural matter.

Consider:
- What documents are legally required under BNSS/Evidence Act?
- What evidence needs to be gathered?
- What forms need to be filled?
- Which items are time-sensitive based on the timeline constraints?

Prioritize items as:
- HIGH: Legally mandatory or time-critical
- MEDIUM: Important but not immediately required
- LOW: Helpful but optional"""
        
<<<<<<< HEAD
        try:
            output = self.llm.invoke(
                [
                    {"role": "system", "content": CHECKLIST_GENERATOR_SYSTEM_PROMPT},
=======
        system_prompt = CIVIL_CHECKLIST_GENERATOR_SYSTEM_PROMPT if active_domain == "civil" else CHECKLIST_GENERATOR_SYSTEM_PROMPT
        
        try:
            output = self.llm.invoke(
                [
                    {"role": "system", "content": system_prompt},
>>>>>>> 14a165ddc199668c3ad8563ab4d99d899b1c0e5e
                    {"role": "user", "content": user_prompt},
                ],
                config={"callbacks": callbacks}
            )
            
            print(f"✅ Generated {len(output.items)} checklist items")
            high_priority = [item for item in output.items if item.priority == "high"]
            print(f"   - High priority: {len(high_priority)}")
            
            return {"checklist": output}
            
        except Exception as e:
            print(f"⚠️  Checklist generation failed: {str(e)[:100]}")
            raise
