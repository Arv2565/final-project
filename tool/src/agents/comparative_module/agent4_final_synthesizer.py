import importlib
import json
from typing import Any, Dict, List

from src.agents.agent_llm_helper import get_agent_llm
from src.models.comparative_module import ComparativeAgent4Output
from src.prompts import comparative_module_prompts as prompts


def observe(name: str = "", as_type: str = ""):
    try:
        decorators_module = importlib.import_module("langfuse.decorators")
        return decorators_module.observe(name=name, as_type=as_type)
    except Exception:
        def decorator(func):
            return func
        return decorator


class Agent4FinalSynthesizer:
    def __init__(self) -> None:
        self.llm = None

    @observe(name="ComparativeModule_Agent4_FinalSynthesizer", as_type="agent")
    def invoke(
        self,
        mode: str,
        state_1: str,
        state_2: str,
        topic: str,
        precomputed_table_markdown: str = "",
        state_1_findings: List[Dict[str, str]] = [],
        state_2_findings: List[Dict[str, str]] = [],
        callbacks: List[Any] = [],
    ) -> ComparativeAgent4Output:
        try:
            if self.llm is None:
                self.llm = get_agent_llm(
                    model_type="writer",
                    output_schema=ComparativeAgent4Output,
                )
            payload = {
                "mode": mode,
                "state_1": state_1,
                "state_2": state_2,
                "topic": topic,
                "precomputed_table_markdown": precomputed_table_markdown,
                "state_1_findings": state_1_findings,
                "state_2_findings": state_2_findings,
            }
            return self.llm.invoke(
                [
                    {"role": "system", "content": prompts.COMPARATIVE_AGENT4_SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=True)},
                ],
                config={"callbacks": callbacks},
            )
        except Exception:
            if mode == "precomputed":
                return ComparativeAgent4Output(
                    intro=prompts.PRECOMPUTED_INTRO_TEMPLATE.format(
                        topic=topic,
                        state_1=state_1,
                        state_2=state_2,
                    ),
                    table_markdown=precomputed_table_markdown,
                    conclusion=prompts.PRECOMPUTED_CONCLUSION_TEMPLATE.format(
                        state_1=state_1,
                        state_2=state_2,
                        topic=(topic or "the topic").lower(),
                    ),
                )

            table_lines = [
                f"| Aspect | {state_1} | {state_2} |",
                "|--------|--------|-----------|",
            ]
            all_aspects: List[str] = []
            map_1 = {item.get("aspect", ""): item.get("value", "") for item in state_1_findings}
            map_2 = {item.get("aspect", ""): item.get("value", "") for item in state_2_findings}
            for item in state_1_findings + state_2_findings:
                aspect = item.get("aspect", "")
                if aspect and aspect not in all_aspects:
                    all_aspects.append(aspect)
            if not all_aspects:
                all_aspects = ["Key point"]
                map_1["Key point"] = prompts.TABLE_NOT_FOUND_VALUE
                map_2["Key point"] = prompts.TABLE_NOT_FOUND_VALUE

            for aspect in all_aspects[:8]:
                left = map_1.get(aspect, prompts.TABLE_NOT_FOUND_VALUE)
                right = map_2.get(aspect, prompts.TABLE_NOT_FOUND_VALUE)
                table_lines.append(f"| {aspect} | {left} | {right} |")

            return ComparativeAgent4Output(
                intro=prompts.FALLBACK_INTRO_TEMPLATE.format(state_1=state_1, state_2=state_2),
                table_markdown="\n".join(table_lines),
                conclusion=prompts.FALLBACK_CONCLUSION_TEMPLATE.format(state_1=state_1, state_2=state_2),
            )
