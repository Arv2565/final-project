import importlib
import json
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from src.agents.comparative_module.agent1_table_selector import Agent1TableSelector
from src.agents.comparative_module.agent2_state1_retriever import Agent2State1Retriever
from src.agents.comparative_module.agent3_state2_retriever import Agent3State2Retriever
from src.agents.comparative_module.agent4_final_synthesizer import Agent4FinalSynthesizer
from src.models.comparative_module import ComparisonEntry, ComparisonMatch
from src.prompts import comparative_module_prompts as prompts


def observe(name: str = "", as_type: str = ""):
    try:
        decorators_module = importlib.import_module("langfuse.decorators")
        return decorators_module.observe(name=name, as_type=as_type)
    except Exception:
        def decorator(func):
            return func
        return decorator


class ComparativeModuleWorkflow:
    def __init__(self) -> None:
        self._entries = self._load_entries()
        self._agent1 = Agent1TableSelector()
        self._agent2 = Agent2State1Retriever()
        self._agent3 = Agent3State2Retriever()
        self._agent4 = Agent4FinalSynthesizer()

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_entries() -> List[ComparisonEntry]:
        raw = json.loads(prompts.COMPARE_INDEX_PATH.read_text(encoding="utf-8"))
        entries: List[ComparisonEntry] = []
        for item in raw.get("entries", []):
            entries.append(
                ComparisonEntry(
                    id=item["id"],
                    topic=item["topic"],
                    states=item["states"],
                    keywords=item.get("keywords", []),
                    aliases=item.get("aliases", []),
                    file_path=item["file_path"],
                    has_table=bool(item.get("has_table", False)),
                    table_headers=item.get("table_headers", ["Aspect", "State 1", "State 2"]),
                    table_row_count=int(item.get("table_row_count", 0)),
                    short_summary=item.get("short_summary", ""),
                )
            )
        return entries

    @observe(name="ComparativeModule_Run", as_type="agent")
    def run(self, query: str, callbacks: List[Any] = []) -> Dict[str, Any]:
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            return {
                "comparison_result": prompts.EMPTY_QUERY_MESSAGE,
                "final_response": prompts.EMPTY_QUERY_MESSAGE,
                "comparison_mode": "error",
            }

        states = sorted({state for entry in self._entries for state in entry.states})
        agent1_output = self._agent1.invoke(cleaned_query, states, callbacks=callbacks)

        if agent1_output.needs_clarification:
            question = agent1_output.clarification_question or prompts.CLARIFICATION_QUESTION_NO_STATES
            return {
                "comparison_mode": "clarification",
                "needs_clarification": True,
                "current_agent": "comparative_module",
                "pending_clarification": {
                    "question": question,
                    "reason": prompts.CLARIFICATION_REASON,
                    "options": states,
                },
            }

        state_1 = agent1_output.state_1.strip()
        state_2 = agent1_output.state_2.strip()
        top_match = self._find_best_match(cleaned_query)

        if top_match and top_match.score >= 1.0:
            table_markdown, preamble = self._load_markdown_table(top_match.entry)
            final_out = self._agent4.invoke(
                mode="precomputed",
                state_1=state_1,
                state_2=state_2,
                topic=top_match.entry.topic,
                precomputed_table_markdown=table_markdown,
                callbacks=callbacks,
            )
            final_markdown = self._format_final(final_out.intro, table_markdown, final_out.conclusion)
            return {
                "comparison_result": final_markdown,
                "final_response": final_markdown,
                "comparison_mode": "precomputed",
                "comparison_match_id": top_match.entry.id,
                "comparison_match_score": top_match.score,
                "comparison_match_terms": top_match.matched_terms,
                "comparison_source_file": top_match.entry.file_path,
                "comparison_preamble": preamble,
            }

        state_1_findings = self._agent2.invoke(cleaned_query, state_1, callbacks=callbacks)
        state_2_findings = self._agent3.invoke(cleaned_query, state_2, callbacks=callbacks)

        final_out = self._agent4.invoke(
            mode="fallback",
            state_1=state_1,
            state_2=state_2,
            topic=agent1_output.topic_hint,
            state_1_findings=[x.model_dump() for x in state_1_findings.findings],
            state_2_findings=[x.model_dump() for x in state_2_findings.findings],
            callbacks=callbacks,
        )
        final_markdown = self._format_final(final_out.intro, final_out.table_markdown, final_out.conclusion)
        return {
            "comparison_result": final_markdown,
            "final_response": final_markdown,
            "comparison_mode": "fallback",
            "comparison_match_id": None,
            "comparison_match_score": 0.0,
            "comparison_match_terms": [],
            "comparison_state_1": state_1,
            "comparison_state_2": state_2,
            "comparison_state_1_findings": [x.model_dump() for x in state_1_findings.findings],
            "comparison_state_2_findings": [x.model_dump() for x in state_2_findings.findings],
        }

    def _find_best_match(self, query: str) -> Optional[ComparisonMatch]:
        normalized_query = self._normalize(query)
        best: Optional[ComparisonMatch] = None

        for entry in self._entries:
            score = 0.0
            matched_terms: List[str] = []

            topic_norm = self._normalize(entry.topic)
            if topic_norm and topic_norm in normalized_query:
                score += 4.0
                matched_terms.append(entry.topic)

            for term in entry.keywords + entry.aliases:
                norm_term = self._normalize(term)
                if norm_term and norm_term in normalized_query:
                    score += 1.0
                    matched_terms.append(term)

            if score > 0 and (best is None or score > best.score):
                best = ComparisonMatch(entry=entry, score=score, matched_terms=matched_terms)

        return best

    def _load_markdown_table(self, entry: ComparisonEntry) -> Tuple[str, str]:
        full_path = prompts.WORKSPACE_ROOT / entry.file_path
        text = full_path.read_text(encoding="utf-8")

        lines = text.splitlines()
        table_lines: List[str] = []
        for line in lines:
            if line.strip().startswith("|"):
                table_lines.append(line.rstrip())

        preamble_lines: List[str] = []
        for line in lines:
            if line.strip().startswith("|"):
                break
            if line.strip():
                preamble_lines.append(line.strip())

        table_markdown = "\n".join(table_lines).strip()
        preamble = " ".join(preamble_lines).strip()
        return table_markdown, preamble

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", text.lower())).strip()

    @staticmethod
    def _format_final(intro: str, table_markdown: str, conclusion: str) -> str:
        return f"{intro}\n\n{table_markdown}\n\n{conclusion}"
