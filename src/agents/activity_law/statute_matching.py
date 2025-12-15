from typing import Dict, Any, List
from src.config import get_llm_config
from src.agents.agent_llm_helper import get_agent_llm
from src.models.activity_law import StatuteMatchingOutput
from src.prompts.activity_law_prompts import STATUTE_MATCHING_PROMPT
from src.models import GraphState

class StatuteMatchingAgent:
    def __init__(self):
        self.llm = get_agent_llm(
            model_type="writer",
            output_schema=StatuteMatchingOutput,
        )

    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        print("\n" + "="*80)
        print("⚖️  STATUTE MATCHING AGENT")
        print("="*80)
        
        # Get input from previous step
        activity_law_state = state.get("activity_law_state")
        if not activity_law_state or not activity_law_state.fact_structuring:
            print("⚠️  StatuteMatchingAgent skipped: No fact structuring output")
            return {"statute_matching": None}

        factors = activity_law_state.fact_structuring.factors
        events = activity_law_state.fact_structuring.events
        
        print(f"\n📥 Input State:")
        print(f"   Factors: {len(factors) if factors else 0} from fact structuring")
        print(f"   Events: {len(events) if events else 0} from fact structuring")
        
        try:
            result = self.llm.invoke(
                STATUTE_MATCHING_PROMPT.format(
                    factors=factors,
                    events=events
                ),
                config={"callbacks": callbacks}
            )
            
            print(f"\n✅ Statute Matching Output:")
            if result and hasattr(result, 'candidate_statutes'):
                print(f"   Candidate Statutes: {len(result.candidate_statutes) if result.candidate_statutes else 0} found")
            print(f"\n📤 Return: statute_matching")
            
            return {"statute_matching": result}
        except Exception as e:
            print(f"\n⚠️  StatuteMatchingAgent failed: {str(e)[:100]}")
            return {"statute_matching": None}
