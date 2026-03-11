import importlib
from typing import Any, List

from src.agents.agent_llm_helper import get_agent_llm
from src.models.comparative_module import ComparativeStateFinding, ComparativeStateFindingsOutput
from src.prompts import comparative_module_prompts as prompts


def observe(name: str = "", as_type: str = ""):
    try:
        decorators_module = importlib.import_module("langfuse.decorators")
        return decorators_module.observe(name=name, as_type=as_type)
    except Exception:
        def decorator(func):
            return func
        return decorator


class Agent2State1Retriever:
    def __init__(self) -> None:
        self.llm = None

    @observe(name="ComparativeModule_Agent2_StateOneRetriever", as_type="agent")
    def invoke(self, query: str, state_name: str, source_context: str = "", callbacks: List[Any] = []) -> ComparativeStateFindingsOutput:
        try:
            if self.llm is None:
                self.llm = get_agent_llm(
                    model_type="writer",
                    output_schema=ComparativeStateFindingsOutput,
                )
            user_prompt = (
                f"User query: {query}\n"
                f"Target state: {state_name}\n"
                f"Source context: {source_context}\n"
                "Generate findings for this state only."
            )
            return self.llm.invoke(
                [
                    {"role": "system", "content": prompts.COMPARATIVE_AGENT2_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                config={"callbacks": callbacks},
            )
        except Exception:
            return ComparativeStateFindingsOutput(
                findings=[
                    ComparativeStateFinding(
                        aspect="Legal dataset availability",
                        value=prompts.FALLBACK_NO_MATCH_ROWS[0]["value"].format(state=state_name),
                    ),
                    ComparativeStateFinding(
                        aspect="Suggested next step",
                        value=prompts.FALLBACK_NO_MATCH_ROWS[1]["value"],
                    ),
                ],
                summary=f"Fallback findings generated for {state_name}.",
            )
