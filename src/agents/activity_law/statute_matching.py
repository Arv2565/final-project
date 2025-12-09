from typing import Dict, Any
from langchain_openai import ChatOpenAI
from src.config import get_llm_config
from src.models.activity_law import StatuteMatchingOutput
from src.prompts.activity_law_prompts import STATUTE_MATCHING_PROMPT
from src.models import GraphState

class StatuteMatchingAgent:
    def __init__(self):
        config = get_llm_config()
        self.llm = ChatOpenAI(
            model=config.writer_model,
            temperature=0
        ).with_structured_output(StatuteMatchingOutput)

    def __call__(self, state: GraphState) -> Dict[str, Any]:
        print("---STATUTE MATCHING AGENT---")
        
        # Get input from previous step
        activity_law_state = state.get("activity_law_state")
        if not activity_law_state or not activity_law_state.fact_structuring:
            print("StatuteMatchingAgent skipped: No fact structuring output")
            return {"statute_matching": None}

        factors = activity_law_state.fact_structuring.factors
        events = activity_law_state.fact_structuring.events
        
        try:
            result = self.llm.invoke(
                STATUTE_MATCHING_PROMPT.format(
                    factors=factors,
                    events=events
                )
            )
            return {"statute_matching": result}
        except Exception as e:
            print(f"StatuteMatchingAgent failed: {e}")
            return {"statute_matching": None}
