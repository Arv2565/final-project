from typing import Dict, Any, List
from src.config import get_llm_config
from src.agents.agent_llm_helper import get_agent_llm
from src.models.activity_law import RuleMatchingOutput
from src.prompts.activity_law_prompts import RULE_MATCHING_PROMPT
from src.models import GraphState

class RuleMatchingAgent:
    def __init__(self):
        self.llm = get_agent_llm(
            model_type="writer",
            output_schema=RuleMatchingOutput,
        )

    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        print("\n" + "="*80)
        print("📜 RULE MATCHING AGENT")
        print("="*80)
        
        activity_law_state = state.get("activity_law_state")
        if not activity_law_state or not activity_law_state.statute_matching:
            print("⚠️  RuleMatchingAgent skipped: Missing statute matching output")
            return {"rule_matching": None}

        factors = activity_law_state.fact_structuring.factors
        events = activity_law_state.fact_structuring.events
        candidate_statutes = activity_law_state.statute_matching.candidate_statutes
        
        print(f"\n📥 Input State:")
        print(f"   Candidate Statutes: {len(candidate_statutes) if candidate_statutes else 0}")
        print(f"   Factors: {len(factors) if factors else 0}")
        print(f"   Events: {len(events) if events else 0}")

        try:
            result = self.llm.invoke(
                RULE_MATCHING_PROMPT.format(
                    candidate_statutes=candidate_statutes,
                    factors=factors,
                    events=events
                ),
                config={"callbacks": callbacks}
            )
            
            print(f"\n✅ Rule Matching Output:")
            if result and hasattr(result, 'rule_assessments'):
                print(f"   Rule Assessments: {len(result.rule_assessments) if result.rule_assessments else 0} created")
            print(f"\n📤 Return: rule_matching")
            
            return {"rule_matching": result}
        except Exception as e:
            print(f"\n⚠️  RuleMatchingAgent failed: {str(e)[:100]}")
            return {"rule_matching": None}
