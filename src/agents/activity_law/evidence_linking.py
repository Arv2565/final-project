from typing import Dict, Any
from langchain_openai import ChatOpenAI
from src.config import get_llm_config
from src.models.activity_law import EvidenceLinkingOutput
from src.prompts.activity_law_prompts import EVIDENCE_LINKING_PROMPT
from src.models import GraphState

class EvidenceLinkingAgent:
    def __init__(self):
        config = get_llm_config()
        self.llm = ChatOpenAI(
            model=config.writer_model,
            temperature=0
        ).with_structured_output(EvidenceLinkingOutput)

    def __call__(self, state: GraphState) -> Dict[str, Any]:
        print("---EVIDENCE LINKING AGENT---")
        
        activity_law_state = state.get("activity_law_state")
        if not activity_law_state or not activity_law_state.risk_assessment:
            print("EvidenceLinkingAgent skipped: Missing risk assessment output")
            return {"evidence_linking": None}

        factors = activity_law_state.fact_structuring.factors
        events = activity_law_state.fact_structuring.events
        risk_matrix = activity_law_state.risk_assessment.risk_matrix

        try:
            result = self.llm.invoke(
                EVIDENCE_LINKING_PROMPT.format(
                    risk_matrix=risk_matrix,
                    factors=factors,
                    events=events
                )
            )
            return {"evidence_linking": result}
        except Exception as e:
            print(f"EvidenceLinkingAgent failed: {e}")
            return {"evidence_linking": None}
