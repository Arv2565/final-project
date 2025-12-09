from typing import Dict, Any
from langchain_openai import ChatOpenAI
from src.config import get_llm_config
from src.models.activity_law import FactStructuringOutput
from src.prompts.activity_law_prompts import FACT_STRUCTURING_PROMPT
from src.models import GraphState

class FactStructuringAgent:
    def __init__(self):
        config = get_llm_config()
        self.llm = ChatOpenAI(
            model=config.writer_model,
            temperature=0
        ).with_structured_output(FactStructuringOutput)

    def __call__(self, state: GraphState) -> Dict[str, Any]:
        print("---FACT STRUCTURING AGENT---")
        query = state["router_output"].cleaned_query
        
        try:
            result = self.llm.invoke(
                FACT_STRUCTURING_PROMPT.format(query=query)
            )
            return {"fact_structuring": result}
        except Exception as e:
            print(f"FactStructuringAgent failed: {e}")
            return {"fact_structuring": None}
