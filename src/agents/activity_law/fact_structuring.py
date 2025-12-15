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
        print(f"   Query: {query[:100]}...")
        
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
            print(f"\n📤 Return: fact_structuring")
            
            return {"fact_structuring": result}
        except Exception as e:
            print(f"\n⚠️  FactStructuringAgent failed: {str(e)[:100]}")
            return {"fact_structuring": None}
