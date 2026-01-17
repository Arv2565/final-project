from typing import Dict, Any, List
from src.models import GraphState
from src.models.procedural_guidance import TimelineConstraintOutput
from src.agents.agent_llm_helper import get_agent_llm
from src.prompts.procedural_prompts import TIMELINE_CONSTRAINT_SYSTEM_PROMPT


class TimelineConstraintAgent:
    """Identifies deadlines, limitation periods, and filing windows based on BNSS."""
    
    def __init__(self):
        self.llm = get_agent_llm(
            model_type="writer",
            output_schema=TimelineConstraintOutput,
        )
    
    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        """Identify timeline constraints from user query.
        
        Args:
            state: GraphState containing router_output
            callbacks: List of LangChain callbacks
            
        Returns:
            Dict with 'timeline_constraints' field
        """
        print("\n🕐 TIMELINE/CONSTRAINT IDENTIFIER AGENT")
        print("=" * 60)
        
        router_output = state.get("router_output")
        if not router_output:
            raise ValueError("Missing 'router_output' in state")
        
        cleaned_query = router_output.cleaned_query
        
        # Clarification Logic
        clarification_counts = state.get("clarification_counts", {})
        current_count = clarification_counts.get("procedural_guidance", 0)
        MAX_CLARIFICATION = 3
        
        clarification_history = state.get("clarification_history", [])
        
        # Build user prompt
        user_prompt = f"""Query: {cleaned_query}

Identify all relevant timeline constraints, deadlines, limitation periods, and filing windows for this procedural matter.

Consider:
- What type of procedural step is this? (FIR, bail, trial, appeal, etc.)
- What are the statutory deadlines under BNSS?
- What are the consequences of missing these deadlines?

Be precise with BNSS section references."""

        if clarification_history:
             user_prompt += "\n\nPrevious Clarifications:\n"
             for item in clarification_history:
                 user_prompt += f"Q: {item.get('question', '')}\nA: {item.get('answer', '')}\n"

        if current_count < MAX_CLARIFICATION:
             user_prompt += "\n\nIf the query is missing critical procedural context (e.g. Jurisdiction, Type of Case/Appeals), you MAY request clarification. Set 'clarification' field and leave 'constraints' empty."
        else:
             user_prompt += "\n\nYou have reached the limit for clarifications. You MUST make best-guess assumptions based on general Indian criminal procedure."
        
        try:
            output = self.llm.invoke(
                [
                    {"role": "system", "content": TIMELINE_CONSTRAINT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                config={"callbacks": callbacks}
            )
            
            print(f"✅ Timeline Agent Output Check")
            
            if output.clarification:
                print(f"   Requesting Clarification: {output.clarification.question}")
                clarification_counts["procedural_guidance"] = current_count + 1
                return {
                    "timeline_constraints": output,
                    "pending_clarification": output.clarification.dict(),
                    "clarification_counts": clarification_counts
                } # Node must handle the merge
            
            print(f"✅ Identified {len(output.constraints)} timeline constraints")
            for constraint in output.constraints:
                print(f"   - {constraint.constraint_type}: {constraint.description}")
            
            return {"timeline_constraints": output}
            
        except Exception as e:
            print(f"⚠️  Timeline constraint identification failed: {str(e)[:100]}")
            raise
