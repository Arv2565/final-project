from typing import Dict, Any
from langchain_openai import ChatOpenAI
from src.config import get_llm_config
from src.models.activity_law import RuleMatchingOutput
from src.prompts.activity_law_prompts import RULE_MATCHING_PROMPT
from src.models import GraphState

class RuleMatchingAgent:
    def __init__(self):
        config = get_llm_config()
        self.llm = ChatOpenAI(
            model=config.writer_model,
            temperature=0
        ).with_structured_output(RuleMatchingOutput)

    def __call__(self, state: GraphState) -> Dict[str, Any]:
        print("---RULE MATCHING AGENT---")
        
        activity_law_state = state.get("activity_law_state")
        if not activity_law_state or not activity_law_state.statute_matching:
            print("RuleMatchingAgent skipped: Missing statute matching output")
            return {"rule_matching": None}

        factors = activity_law_state.fact_structuring.factors
        events = activity_law_state.fact_structuring.events
        candidate_statutes = activity_law_state.statute_matching.candidate_statutes

        try:
            result = self.llm.invoke(
                RULE_MATCHING_PROMPT.format(
                    candidate_statutes=candidate_statutes,
                    factors=factors,
                    events=events
                )
            )
            return {"rule_matching": result}
        except Exception as e:
            print(f"RuleMatchingAgent failed: {e}")
            return {"rule_matching": None}
