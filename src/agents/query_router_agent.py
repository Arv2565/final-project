from typing import Dict, Any

from langchain_openai import ChatOpenAI

from src.models import GraphState, QueryRouterOutput, QueryMetadata
from src.config import get_llm_config
from src.prompts.query_router_agent import QUERY_ROUTER_SYSTEM_PROMPT


class QueryRouterAgent:
    """Normalizes queries, translates to English, and extracts metadata.
    
    This agent is the first step in the legal query processing pipeline.
    It takes the raw user input and produces a cleaned, English version
    along with basic metadata about the query.
    """

    def __init__(self) -> None:
        config = get_llm_config()
        self.llm = ChatOpenAI(
            model=config.research_model,
            temperature=config.temperature_research,
        ).with_structured_output(QueryRouterOutput)

    def __call__(self, state: GraphState) -> Dict[str, Any]:
        """Process user query through query router.
        
        Args:
            state: GraphState containing 'user_query' field
            
        Returns:
            Dict with 'router_output' field containing QueryRouterOutput
            
        Raises:
            ValueError: If user_query is missing from state
        """
        user_query = state.get("user_query", "").strip()
        if not user_query:
            raise ValueError("GraphState missing 'user_query' for QueryRouterAgent")

        try:
            # LangChain handles structured output binding and validation
            router_output = self.llm.invoke([
                {"role": "system", "content": QUERY_ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Process this query:\n{user_query}"},
            ])
            
            return {"router_output": router_output}
            
        except Exception as e:
            # Fallback: If LLM fails to produce valid structured output,
            # pass through the original query with default metadata
            fallback_output = QueryRouterOutput(
                cleaned_query=user_query,
                metadata=QueryMetadata(
                    language="en",
                    has_personal_data=False,
                    is_legal_question=True
                )
            )
            return {"router_output": fallback_output}
