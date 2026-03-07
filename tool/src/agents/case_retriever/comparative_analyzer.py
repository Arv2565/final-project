"""
Case Comparative Analyzer Agent for Case Retrieval Module.

This agent sends retrieved lower and upper court cases to an LLM,
which returns a concise markdown analysis and relevant PDF paths.
"""

import logging
import json
from typing import List, Dict, Any, Optional, Set
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.agents.agent_llm_helper import get_agent_llm
from src.agents.case_retriever.models import (
    LowerCourtCaseResult,
    UpperCourtCaseResult,
    CaseSynthesisResult,
)

logger = logging.getLogger(__name__)

# Langfuse integration
try:
    from langfuse.decorators import observe
except ImportError:
    # Fallback if langfuse not available
    def observe(name: str = "", as_type: str = ""):
        def decorator(func):
            return func
        return decorator


class CaseComparativeAnalyzerAgent:
    """Generates final case synthesis from retrieved case inputs."""

    def __init__(self) -> None:
        self.llm = get_agent_llm(
            model_type="writer",
            output_schema=CaseSynthesisResult,
        )
    
    @observe(name="CaseComparativeAnalyzer", as_type="agent")
    def __call__(
        self,
        lower_result: Optional[LowerCourtCaseResult],
        upper_result: Optional[UpperCourtCaseResult],
        state: Optional[Dict[str, Any]] = None,
        callbacks: Optional[List] = None
    ) -> Dict[str, Any]:
        """
        Generate LLM synthesis from lower and upper court case results.
        
        Args:
            lower_result: LowerCourtCaseResult from lower court finder (optional)
            upper_result: UpperCourtCaseResult from upper court finder (optional)
            state: GraphState
            callbacks: Optional callbacks
        
        Returns:
            Dict with 'analysis_result' key containing CaseSynthesisResult
        """
        try:
            lower_count = len(lower_result.cases) if lower_result else 0
            upper_count = len(upper_result.precedents) if upper_result else 0
            
            logger.info(
                f"CaseComparativeAnalyzer: Analyzing "
                f"{lower_count} lower cases, {upper_count} precedents"
            )

            # Handle edge cases
            if not lower_result and not upper_result:
                logger.warning("CaseComparativeAnalyzer: Both lower and upper results are None")
                return {"analysis_result": CaseSynthesisResult(
                    analysis_markdown="# Case Analysis\n\nNo cases found for the query.",
                    relevant_pdf_paths=[]
                )}

            cases_payload = self._prepare_cases_payload(lower_result, upper_result)
            analysis_result = self._run_llm_synthesis(
                cases_payload=cases_payload,
                user_query=(state or {}).get("user_query", ""),
                callbacks=callbacks or [],
            )

            logger.info(
                f"CaseComparativeAnalyzer: Analysis complete. "
                f"Found {len(analysis_result.relevant_pdf_paths)} relevant PDFs"
            )

            return {"analysis_result": analysis_result}

        except Exception as e:
            logger.error(f"CaseComparativeAnalyzer error: {e}", exc_info=True)
            # Return safe fallback instead of raising
            return {"analysis_result": CaseSynthesisResult(
                analysis_markdown="# Case Analysis\n\nAn error occurred during analysis. Please try again.",
                relevant_pdf_paths=[]
            )}

    def _prepare_cases_payload(
        self,
        lower_result: Optional[LowerCourtCaseResult],
        upper_result: Optional[UpperCourtCaseResult],
    ) -> List[Dict[str, Any]]:
        """Build compact case payload consumed by the LLM."""
        payload: List[Dict[str, Any]] = []

        if lower_result:
            for case in lower_result.cases:
                payload.append(
                    {
                        "source": "lower",
                        "case_id": case.case_id,
                        "citation": case.citation,
                        "court": case.court,
                        "date": case.date,
                        "decision": case.decision,
                        "legal_concepts": case.legal_concepts,
                        "statutes_mentioned": case.statutes_mentioned,
                        "content_preview": case.content_preview,
                        "relevance_score": case.similarity_score,
                        "pdf_path": case.pdf_path,
                    }
                )

        if upper_result:
            for precedent in upper_result.precedents:
                payload.append(
                    {
                        "source": "upper",
                        "case_id": None,
                        "citation": precedent.citation,
                        "court": precedent.court,
                        "date": precedent.date,
                        "decision": precedent.decision,
                        "legal_concepts": precedent.common_concepts,
                        "statutes_mentioned": [],
                        "content_preview": None,
                        "relevance_score": precedent.relevance_score,
                        "pdf_path": precedent.pdf_path,
                    }
                )

        return payload

    @observe(name="LLM_Synthesis", as_type="llm")
    def _run_llm_synthesis(
        self,
        cases_payload: List[Dict[str, Any]],
        user_query: str,
        callbacks: List[Any],
    ) -> CaseSynthesisResult:
        """Invoke LLM to produce markdown analysis and relevant PDF paths."""
        available_pdf_paths = {
            path for path in (case.get("pdf_path") for case in cases_payload) if path
        }

        if not cases_payload:
            logger.info("No cases in payload - returning default message")
            return CaseSynthesisResult(
                analysis_markdown="# Case Analysis\n\nNo relevant cases were found for the query.",
                relevant_pdf_paths=[],
            )

        prompt = (
            "You are a legal case synthesis assistant.\n"
            "Read the case JSON and produce ONLY structured output.\n"
            "Return exactly two fields:\n"
            "1) analysis_markdown: markdown containing\n"
            "   - a short summary of relevant cases\n"
            "   - description of the most relevant cases\n"
            "   - a conclusion\n"
            "2) relevant_pdf_paths: list of PDF paths selected ONLY from provided case json pdf_path values.\n"
            "Do not invent pdf paths.\n\n"
            f"User query: {user_query}\n\n"
            "Case input JSON:\n"
            f"{json.dumps(cases_payload, ensure_ascii=False, indent=2)}"
        )

        try:
            logger.info(f"Invoking LLM synthesis with {len(cases_payload)} cases...")
            logger.info(f"Case sources: {set(c.get('source') for c in cases_payload)}")
            logger.info(f"Available PDF paths: {len({c.get('pdf_path') for c in cases_payload if c.get('pdf_path')})}")
            llm_result = self.llm.invoke(
                [
                    {"role": "system", "content": "You are a precise legal analysis assistant."},
                    {"role": "user", "content": prompt},
                ],
                config={"callbacks": callbacks},
            )
            logger.info(f"LLM synthesis returned: {type(llm_result)}")
            
            # Ensure result has required fields
            if not hasattr(llm_result, 'analysis_markdown'):
                logger.error(f"LLM result missing analysis_markdown field. Type: {type(llm_result)}")
                raise ValueError("LLM output missing analysis_markdown")
            
            filtered_paths = self._filter_paths(llm_result.relevant_pdf_paths or [], available_pdf_paths)
            
            result = CaseSynthesisResult(
                analysis_markdown=llm_result.analysis_markdown or "# Case Analysis\n\nNo synthesis generated.",
                relevant_pdf_paths=filtered_paths,
            )
            logger.info(f"LLM synthesis successful: {len(result.analysis_markdown)} chars markdown, {len(result.relevant_pdf_paths)} PDFs")
            return result
            
        except Exception as llm_error:
            logger.error(f"CaseComparativeAnalyzer LLM synthesis failed: {llm_error}", exc_info=True)
            
            # Provide detailed fallback with all available case citations
            fallback_paths = sorted(available_pdf_paths)
            case_citations = [
                f"- {case.get('citation', 'Unknown')} ({case.get('source', 'unknown').upper()}, {case.get('court', 'Unknown court')})"
                for case in cases_payload[:15]
            ]
            
            fallback_markdown = (
                "# Case Analysis\n\n"
                "The system encountered an error during LLM synthesis. Here are the retrieved cases:\n\n"
                "## Retrieved Cases\n"
                + "\n".join(case_citations) +
                "\n\n## Note\n"
                "Please try again or contact support if the issue persists."
            )
            
            logger.warning(f"Returning fallback with {len(fallback_paths)} PDFs and {len(case_citations)} case descriptions")
            return CaseSynthesisResult(
                analysis_markdown=fallback_markdown,
                relevant_pdf_paths=fallback_paths,
            )

    def _filter_paths(self, paths: List[str], allowed_paths: Set[str]) -> List[str]:
        """Keep only PDF paths that exist in input cases."""
        seen: Set[str] = set()
        filtered: List[str] = []
        for path in paths or []:
            if path in allowed_paths and path not in seen:
                seen.add(path)
                filtered.append(path)
        return filtered
