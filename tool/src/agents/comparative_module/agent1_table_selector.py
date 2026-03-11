import importlib
from typing import Any, List

from src.agents.agent_llm_helper import get_agent_llm
from src.models.comparative_module import ComparativeAgent1Output
from src.prompts import comparative_module_prompts as prompts


def observe(name: str = "", as_type: str = ""):
    try:
        decorators_module = importlib.import_module("langfuse.decorators")
        return decorators_module.observe(name=name, as_type=as_type)
    except Exception:
        def decorator(func):
            return func
        return decorator


class Agent1TableSelector:
    def __init__(self) -> None:
        self.llm = None

    @observe(name="ComparativeModule_Agent1_TableSelector", as_type="agent")
    def invoke(self, query: str, available_states: List[str], callbacks: List[Any] = []) -> ComparativeAgent1Output:
        try:
            if self.llm is None:
                self.llm = get_agent_llm(
                    model_type="writer",
                    output_schema=ComparativeAgent1Output,
                )
            user_prompt = (
                f"User query: {query}\n"
                f"Available states: {', '.join(available_states)}\n"
                "Return extracted states, topic hint, and clarification decision."
            )
            result = self.llm.invoke(
                [
                    {"role": "system", "content": prompts.COMPARATIVE_AGENT1_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                config={"callbacks": callbacks},
            )
            return result
        except Exception:
            # Deterministic fallback for environments without LLM credentials
            normalized_query = (query or "").lower()
            found = [state for state in available_states if state.lower() in normalized_query]
            if len(found) >= 2:
                return ComparativeAgent1Output(
                    needs_clarification=False,
                    state_1=found[0],
                    state_2=found[1],
                    topic_hint="legal comparison",
                    reasoning="Fallback extraction by state-name matching",
                    clarification_question="",
                )
            if len(found) == 1:
                question = prompts.CLARIFICATION_QUESTION_SINGLE_STATE.format(state=found[0])
            else:
                question = prompts.CLARIFICATION_QUESTION_NO_STATES
            return ComparativeAgent1Output(
                needs_clarification=True,
                state_1="",
                state_2="",
                topic_hint="",
                reasoning="Fallback requested clarification due to missing state pair",
                clarification_question=question,
            )
