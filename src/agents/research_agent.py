from typing import Dict, Any

from src.state import GraphState
from src.config import get_openai_client, get_llm_config
from src.prompts.research_agent import RESEARCH_AGENT_SYSTEM_PROMPT


class ResearchAgent:
    """Reads the question from state and produces structured research notes."""

    def __init__(self) -> None:
        self.client = get_openai_client()
        self.config = get_llm_config()

    def __call__(self, state: GraphState) -> Dict[str, Any]:
        question = state.get("question", "").strip()
        if not question:
            raise ValueError("GraphState missing 'question' for ResearchAgent")

        system_prompt = RESEARCH_AGENT_SYSTEM_PROMPT
        user_prompt = f"User question:\n{question}"

        response = self.client.chat.completions.create(
            model=self.config.research_model,
            temperature=self.config.temperature_research,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        research_notes = response.choices[0].message.content or ""

        # Return a partial state update; LangGraph will merge it.
        return {"research_notes": research_notes}
