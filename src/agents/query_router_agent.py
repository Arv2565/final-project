from typing import Dict, Any, List

from src.models import GraphState, QueryRouterOutput, QueryMetadata
from src.config import get_llm_config
from src.agents.agent_llm_helper import get_agent_llm
from src.prompts.query_router_agent import QUERY_ROUTER_SYSTEM_PROMPT


class QueryRouterAgent:
    """Normalizes queries, translates to English, and extracts metadata.
    
    This agent is the first step in the legal query processing pipeline.
    It takes the raw user input and produces a cleaned, English version
    along with basic metadata about the query.
    """

    def __init__(self) -> None:
        self.llm = get_agent_llm(
            model_type="research",
            output_schema=QueryRouterOutput,
        )

    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        """Process user query through query router.
        
        Args:
            state: GraphState containing 'user_query' field
            callbacks: List of LangChain callbacks
            
        Returns:
            Dict with 'router_output' field containing QueryRouterOutput
            
        Raises:
            ValueError: If user_query is missing from state
        """
        print("\n" + "="*80)
        print("🔄 QUERY ROUTER AGENT")
        print("="*80)
        print(f"\n📥 Input State:")
        print(f"   user_query: {state.get('user_query', '')[:100]}...")
        
        user_query = state.get("user_query", "").strip()
        if not user_query:
            raise ValueError("GraphState missing 'user_query' for QueryRouterAgent")

        try:
            # LangChain handles structured output binding and validation
            router_output = self.llm.invoke(
                [
                    {"role": "system", "content": QUERY_ROUTER_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Process this query:\n{user_query}"},
                ],
                config={"callbacks": callbacks}
            )
            
            print(f"\n✅ Router Output:")
            print(f"   Cleaned Query: {router_output.cleaned_query[:100]}...")
            print(f"   Language: {router_output.metadata.language}")
            print(f"   Has Personal Data: {router_output.metadata.has_personal_data}")
            print(f"   Is Legal Question: {router_output.metadata.is_legal_question}")
            print(f"\n📤 Return: router_output")
            
            return {"router_output": router_output}
            
        except Exception as e:
            print(f"\n⚠️  Router failed, using fallback: {str(e)[:100]}")
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
