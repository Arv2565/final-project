import json
from typing import Dict, Any

from src.models import GraphState, QueryRouterOutput, QueryMetadata
from src.config import get_openai_client, get_llm_config
from src.prompts.query_router_agent import QUERY_ROUTER_SYSTEM_PROMPT


class QueryRouterAgent:
    """Normalizes queries, translates to English, and extracts metadata.
    
    This agent is the first step in the legal query processing pipeline.
    It takes the raw user input and produces a cleaned, English version
    along with basic metadata about the query.
    """

    def __init__(self) -> None:
        self.client = get_openai_client()
        self.config = get_llm_config()

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

        # Single LLM call with strict JSON mode
        response = self.client.chat.completions.create(
            model=self.config.research_model,
            temperature=self.config.temperature_research,
            response_format={"type": "json_object"},  # Enforce JSON output
            messages=[
                {"role": "system", "content": QUERY_ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Process this query:\n{user_query}"},
            ],
        )

        # Parse JSON response
        content = response.choices[0].message.content or "{}"
        try:
            result = json.loads(content)
            
            # Construct Pydantic models for validation
            metadata = QueryMetadata(**result.get("metadata", {}))
            router_output = QueryRouterOutput(
                cleaned_query=result.get("cleaned_query", user_query),
                metadata=metadata
            )
            
            # Return state update - LangGraph will merge this
            # Note: We return the Pydantic model directly; LangGraph handles serialization
            return {"router_output": router_output}
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Fallback: If LLM doesn't return valid JSON, pass through the original query
            # with default metadata
            fallback_output = QueryRouterOutput(
                cleaned_query=user_query,
                metadata=QueryMetadata(
                    language="en",
                    has_personal_data=False,
                    is_legal_question=True
                )
            )
            return {"router_output": fallback_output}
