from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from src.config import get_llm_config
from src.models.activity_law import RiskAssessmentOutput
from src.prompts.activity_law_prompts import RISK_ASSESSMENT_PROMPT
from src.models import GraphState

class RiskAssessmentAgent:
    def __init__(self):
        config = get_llm_config()
        self.llm = ChatOpenAI(
            model=config.writer_model,
            temperature=0
        ).with_structured_output(RiskAssessmentOutput)

    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        print("---RISK ASSESSMENT AGENT---")
        
        activity_law_state = state.get("activity_law_state")
        if not activity_law_state or not activity_law_state.rule_matching:
            print("RiskAssessmentAgent skipped: Missing rule matching output")
            return {"risk_assessment": None}

        factors = activity_law_state.fact_structuring.factors
        events = activity_law_state.fact_structuring.events
        rule_assessments = activity_law_state.rule_matching.rule_assessments

        try:
            result = self.llm.invoke(
                RISK_ASSESSMENT_PROMPT.format(
                    rule_assessments=rule_assessments,
                    factors=factors,
                    events=events
                ),
                config={"callbacks": callbacks}
            )
            return {"risk_assessment": result}
        except Exception as e:
            print(f"RiskAssessmentAgent failed: {e}")
            return {"risk_assessment": None}
