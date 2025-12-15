from typing import Dict, Any, List
from src.config import get_llm_config
from src.agents.agent_llm_helper import get_agent_llm
from src.models.activity_law import RiskAssessmentOutput
from src.prompts.activity_law_prompts import RISK_ASSESSMENT_PROMPT
from src.models import GraphState

class RiskAssessmentAgent:
    def __init__(self):
        self.llm = get_agent_llm(
            model_type="writer",
            output_schema=RiskAssessmentOutput,
        )

    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        print("\n" + "="*80)
        print("⚠️  RISK ASSESSMENT AGENT ⭐")
        print("="*80)
        
        activity_law_state = state.get("activity_law_state")
        if not activity_law_state or not activity_law_state.rule_matching:
            print("⚠️  RiskAssessmentAgent skipped: Missing rule matching output")
            return {"risk_assessment": None}

        factors = activity_law_state.fact_structuring.factors
        events = activity_law_state.fact_structuring.events
        rule_assessments = activity_law_state.rule_matching.rule_assessments
        
        print(f"\n📥 Input State:")
        print(f"   Rule Assessments: {len(rule_assessments) if rule_assessments else 0} to evaluate")
        print(f"   Factors: {len(factors) if factors else 0}")
        print(f"   Events: {len(events) if events else 0}")

        try:
            result = self.llm.invoke(
                RISK_ASSESSMENT_PROMPT.format(
                    rule_assessments=rule_assessments,
                    factors=factors,
                    events=events
                ),
                config={"callbacks": callbacks}
            )
            
            print(f"\n✅ Risk Assessment Output:")
            if result and hasattr(result, 'risk_level'):
                print(f"   Risk Level: {result.risk_level}")
            if result and hasattr(result, 'risk_matrix'):
                print(f"   Risk Matrix: Available with severity levels")
            print(f"\n📤 Return: risk_assessment")
            
            return {"risk_assessment": result}
        except Exception as e:
            print(f"\n⚠️  RiskAssessmentAgent failed: {str(e)[:100]}")
            return {"risk_assessment": None}
