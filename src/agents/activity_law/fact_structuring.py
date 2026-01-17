from typing import Dict, Any, List, Optional
from src.config import get_llm_config
from src.agents.agent_llm_helper import get_agent_llm
from src.models.activity_law import FactStructuringOutput
from src.prompts.activity_law_prompts import FACT_STRUCTURING_PROMPT
from src.models import GraphState

class FactStructuringAgent:
    def __init__(self):
        self.llm = get_agent_llm(
            model_type="writer",
            output_schema=FactStructuringOutput,
        )

    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        print("\n" + "="*80)
        print("📋 FACT STRUCTURING AGENT")
        print("="*80)
        
        query = state["router_output"].cleaned_query
        print(f"\n📥 Input State:")
        import json
        print(json.dumps({k: str(v) for k, v in state.items()}, indent=2))
        
        
        # Clarification Logic
        clarification_counts = state.get("clarification_counts", {})
        current_count = clarification_counts.get("fact_structuring", 0)
        MAX_CLARIFICATION = 3 
        
        clarification_history = state.get("clarification_history", [])
        
        prompt = FACT_STRUCTURING_PROMPT.format(query=query)
        
        if clarification_history:
             prompt += "\n\nPrevious Clarifications:\n"
             for item in clarification_history:
                 prompt += f"Q: {item.get('question', '')}\nA: {item.get('answer', '')}\n"
        
        if current_count < MAX_CLARIFICATION:
             prompt += "\nIf the incident description is missing critical details (e.g. Jurisdiction, specific actions), you MAY request clarification. Set 'clarification' field and leave factors/events empty."
        else:
             prompt += "\nYou have reached the limit for clarifications. You MUST make a best-guess extraction."

        try:
            result = self.llm.invoke(
                prompt,
                config={"callbacks": callbacks}
            )
            
            print(f"\n✅ Fact Structuring Output:")
            if result.clarification:
                print(f"   Requesting Clarification: {result.clarification.question}")
                clarification_counts["fact_structuring"] = current_count + 1
                return {
                    "fact_structuring": result,
                    "pending_clarification": result.clarification.dict(),
                    "clarification_counts": clarification_counts
                }

            if result and hasattr(result, 'factors'):
                print(f"   Factors: {len(result.factors) if result.factors else 0} identified")
            if result and hasattr(result, 'events'):
                print(f"   Events: {len(result.events) if result.events else 0} identified")
            
            # Construct nested state update
            # Note: For Activity to Law agents, the state structure is nested
            # We need to simulate the nested update for logging
            from src.models.activity_law import ActivityLawState
            activity_state = state.get("activity_law_state", ActivityLawState())
            
            # For logging purpose, we can show we are returning the object
            print(f"\n📤 Return: {result}")
            
            return {"fact_structuring": result}
        except Exception as e:
            print(f"\n⚠️  FactStructuringAgent failed: {str(e)[:100]}")
            # If failing, default to None? OR maybe empty result
            # Returning None might break next steps, but error handling is outside scope right now
            return {"fact_structuring": None}
