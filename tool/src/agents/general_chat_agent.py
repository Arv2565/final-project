from typing import Dict, Any, List
from pydantic import BaseModel, Field

from src.models import GraphState
from src.agents.agent_llm_helper import get_agent_llm
from src.prompts.general_chat_agent import GENERAL_CHAT_SYSTEM_PROMPT

class GeneralChatOutput(BaseModel):
    response: str = Field(description="The friendly response to the user, strictly max 2 lines, plus the required follow-up question.")

class GeneralChatAgent:
    """Handles friendly non-legal queries."""

    def __init__(self) -> None:
        self.llm = get_agent_llm(
            model_type="fast",  # Use fast model for chitchat
            output_schema=GeneralChatOutput,
        )

    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        """Process friendly query.
        
        Args:
            state: GraphState containing 'user_query'
            callbacks: List of LangChain callbacks
            
        Returns:
            Dict with 'final_response' field
        """
        print("\n" + "="*80)
        print("💬 GENERAL CHAT AGENT")
        print("="*80)
        
        user_query = state.get("user_query", "").strip()
        
        try:
            output = self.llm.invoke(
                [
                    {"role": "system", "content": GENERAL_CHAT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_query},
                ],
                config={"callbacks": callbacks}
            )
            
            print(f"\n✅ Friendly Response: {output.response}")
            
            return {"final_response": output.response}
            
        except Exception as e:
            print(f"\n⚠️  General Chat failed: {e}")
            return {"final_response": "I am a legal assistant. How can I help you?"}
