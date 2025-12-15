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
        
        try:
            result = self.llm.invoke(
                FACT_STRUCTURING_PROMPT.format(query=query),
                config={"callbacks": callbacks}
            )
            
            print(f"\n✅ Fact Structuring Output:")
            if result and hasattr(result, 'factors'):
                print(f"   Factors: {len(result.factors) if result.factors else 0} identified")
            if result and hasattr(result, 'events'):
                print(f"   Events: {len(result.events) if result.events else 0} identified")
            
            # Construct nested state update
            # Note: For Activity to Law agents, the state structure is nested
            # We need to simulate the nested update for logging
            from src.models.activity_law import ActivityLawState
            activity_state = state.get("activity_law_state", ActivityLawState())
            # We can't easily deep copy the pydantic model in the log simulation without some effort,
            # but we can show the update dict.
            
            # Only update the specific field for logging viz
            if result and hasattr(result, 'fact_structuring'): # This might be direct result object, check schema
                 # result IS the FactStructuringOutput
                 pass

            # Since 'result' IS the output object (FactStructuringOutput), and not a dict with key 'fact_structuring'
            # (Wait, check output_schema=FactStructuringOutput)
            
            # The node wrapper handles the nesting.
            # Here we just return the result.
            
            # For logging purpose, we can show we are returning the object
            print(f"\n📤 Return: {result}")
            
            return {"fact_structuring": result}
        except Exception as e:
            print(f"\n⚠️  FactStructuringAgent failed: {str(e)[:100]}")
            return {"fact_structuring": None}
