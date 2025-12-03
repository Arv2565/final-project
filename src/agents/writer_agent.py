from typing import Dict, Any

from src.state import GraphState
from src.config import get_openai_client, get_llm_config
from src.prompts.writer_agent import WRITER_AGENT_SYSTEM_PROMPT


class WriterAgent:
    """Takes research notes + instructions and produces a polished answer."""

    def __init__(self) -> None:
        self.client = get_openai_client()
        self.config = get_llm_config()

    def __call__(self, state: GraphState) -> Dict[str, Any]:
        question = state.get("question", "").strip()
        research_notes = state.get("research_notes", "").strip()
        instructions = state.get("instructions", "").strip()

        if not question:
            raise ValueError("GraphState missing 'question' for WriterAgent")
        if not research_notes:
            raise ValueError("GraphState missing 'research_notes' for WriterAgent")

        base_system_prompt = WRITER_AGENT_SYSTEM_PROMPT

        if instructions:
            system_prompt = (
                base_system_prompt
                + "\n\nAdditional authoring instructions from the user:\n"
                + instructions
            )
        else:
            system_prompt = base_system_prompt

        user_prompt = (
            f"Original question:\n{question}\n\n"
            f"Research notes:\n{research_notes}\n\n"
            "Now write the final answer for the user."
        )

        response = self.client.chat.completions.create(
            model=self.config.writer_model,
            temperature=self.config.temperature_writer,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        answer = response.choices[0].message.content or ""
        return {"answer": answer}
