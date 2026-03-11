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
from src.agents.case_retriever.models import CaseSynthesisResult
from src.services.case_json_loader import CaseJSONLoader

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
        self.case_loader = CaseJSONLoader()
    
    @observe(name="CaseComparativeAnalyzer", as_type="agent")
    def __call__(
        self,
        lower_citations: List[str],
        upper_citations: List[str],
        state: Optional[Dict[str, Any]] = None,
        callbacks: Optional[List] = None
    ) -> Dict[str, Any]:
        """
        Generate LLM synthesis from citation lists by enriching with full case JSON.
        
        Args:
            lower_citations: List of max 2 citations from lower court finder
            upper_citations: List of max 2 citations from upper court finder
            state: GraphState
            callbacks: Optional callbacks
        
        Returns:
            Dict with 'analysis_result' key containing CaseSynthesisResult
        """
        try:
            logger.info(
                f"CaseComparativeAnalyzer: Analyzing "
                f"{len(lower_citations)} lower citations, {len(upper_citations)} upper citations"
            )

            # Handle edge cases
            if not lower_citations and not upper_citations:
                logger.warning("CaseComparativeAnalyzer: No citations provided")
                return {"analysis_result": CaseSynthesisResult(
                    analysis_markdown="# Case Analysis\n\nNo cases found for the query.",
                    relevant_pdf_paths=[]
                )}

            # Enrich citations with full case JSON from casefiles.json
            enriched_cases = self._enrich_citations_with_full_json(
                lower_citations, upper_citations
            )
            
            if not enriched_cases:
                logger.warning("CaseComparativeAnalyzer: No cases found in casefiles.json")
                return {"analysis_result": CaseSynthesisResult(
                    analysis_markdown="# Case Analysis\n\nSelected cases not found in database.",
                    relevant_pdf_paths=[]
                )}
            
            analysis_result = self._run_llm_synthesis(
                enriched_cases=enriched_cases,
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

    def _enrich_citations_with_full_json(
        self,
        lower_citations: List[str],
        upper_citations: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Enrich citations with full case JSON from casefiles.json.
        
        Args:
            lower_citations: Citations from lower court finder
            upper_citations: Citations from upper court finder
        
        Returns:
            List of enriched case dictionaries with full JSON and metadata
        """
        enriched_cases = []
        
        # Process lower court citations
        for citation in lower_citations:
            logger.info(f"Loading lower court case: {citation}")
            case_json = self.case_loader.load_case_by_citation(citation)
            if case_json:
                enriched_cases.append({
                    "source": "lower_court",
                    "citation": citation,
                    "full_case_json": case_json
                })
            else:
                logger.warning(f"Case not found in casefiles.json: {citation}")
        
        # Process upper court citations
        for citation in upper_citations:
            logger.info(f"Loading upper court case: {citation}")
            case_json = self.case_loader.load_case_by_citation(citation)
            if case_json:
                enriched_cases.append({
                    "source": "upper_court",
                    "citation": citation,
                    "full_case_json": case_json
                })
            else:
                logger.warning(f"Case not found in casefiles.json: {citation}")
        
        logger.info(f"Enriched {len(enriched_cases)} cases with full JSON")
        return enriched_cases

    def _prepare_cases_for_llm(
        self,
        enriched_cases: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Build detailed case payload for LLM from enriched cases with full JSON.
        
        Extracts all relevant fields from the full case JSON structure including:
        - Metadata (court, date, citation, bench)
        - Issues and their outcomes
        - Ratio decidendi
        - Holdings and decisions
        - Statutes interpreted
        - Legal concepts
        - PDF paths from evidence
        """
        payload: List[Dict[str, Any]] = []

        for case_data in enriched_cases:
            case_json = case_data.get("full_case_json", {})
            metadata = case_json.get("metadata", {})
            evidence = case_json.get("evidence", {})
            holding = case_json.get("holding", {})
            ratio = case_json.get("ratio", {})
            
            # Build comprehensive case representation
            case_for_llm = {
                "source": case_data.get("source"),
                "citation": case_data.get("citation"),
                "court": metadata.get("court", ""),
                "bench": metadata.get("bench", []),
                "date": metadata.get("date", ""),
                "language": metadata.get("language", "en"),
                "issues": case_json.get("issues", []),
                "ratio": ratio.get("text", ""),
                "holding": holding,
                "statutes_interpreted": case_json.get("statutes_interpreted", []),
                "legal_concepts": case_json.get("legal_concepts", []),
                "pdf_path": evidence.get("pdf_path", ""),
                "relevant_page_ranges": evidence.get("relevant_page_ranges", []),
                # Include full case json for comprehensive analysis
                "full_structure": case_json
            }
            
            payload.append(case_for_llm)

        return payload

    @observe(name="LLM_Synthesis", as_type="llm")
    def _run_llm_synthesis(
        self,
        enriched_cases: List[Dict[str, Any]],
        user_query: str,
        callbacks: List[Any],
    ) -> CaseSynthesisResult:
        """Invoke LLM to produce markdown analysis and relevant PDF paths from enriched cases."""
        # Prepare detailed payload for LLM
        cases_payload = self._prepare_cases_for_llm(enriched_cases)
        
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
            system_prompt = """You are DIKE, an AI legal analyst specializing in Indian law.

Your task is NOT to produce short summaries.
Your task is to produce detailed legal explanations of ONLY the RELEVANT cases so that a user can clearly understand:

- the factual background of the case
- the legal issues involved
- the arguments of the parties
- the statutes or constitutional provisions involved
- the reasoning of the court
- the final holding and legal principles established

CRITICAL CASE FILTERING RULES:

1. FIRST, analyze the user query to understand what they are asking about.
2. ONLY analyze cases that are directly relevant and address the user's specific query.
3. COMPLETELY EXCLUDE any case that is not directly relevant to the user's legal problem or question.
4. Do NOT include cases that only tangentially relate to the query.
5. Do NOT acknowledge the existence of irrelevant cases.
6. Do NOT include explanatory notes like "Note: This case is not relevant" or "This case is tangential" - simply omit irrelevant cases completely.
7. Present ONLY the relevant cases without any mention of excluded cases.
8. If ALL cases are irrelevant, respond with: "No relevant cases found for this query."

When presenting relevant cases, follow this structured format:

------------------------------------------------------------

CASE ANALYSIS

Case Name:
Citation:
Court:
Bench:
Date:

1. Background Facts
Explain the factual background of the dispute in detail.
Describe the events that led to the litigation and why the case reached the court.

2. Legal Issues
Clearly list the legal questions that the court had to decide.

3. Statutory Framework
Mention all relevant statutes, constitutional provisions, or legal doctrines that the court relied upon.

4. Arguments
Explain the key arguments made by the petitioner/appellant and the respondent.

5. Court's Reasoning
Provide a detailed explanation of how the court analyzed the issues.
Explain the legal reasoning step-by-step.

6. Holding / Judgment
State the final decision of the court and the legal rule that emerged.

7. Key Legal Principles
List the important principles or precedents established by the judgment.

------------------------------------------------------------

IMPORTANT RULES:

1. Do NOT produce short summaries.
2. Do NOT compress the reasoning.
3. Explain the case in a detailed narrative form.
4. Always mention the citation and court if available.
5. If multiple cases are relevant, analyze each case separately using the structured format above.
6. Focus on legally decisive facts and reasoning rather than generic commentary.
7. Preserve legal terminology accurately.
8. Only provide detailed analysis for cases that directly address the user's query.
9. COMPLETELY filter out irrelevant cases - do NOT include any mention of them.
10. Do NOT add explanatory notes about why cases are excluded.

Your goal is to help the user understand the full legal significance of RELEVANT cases ONLY, not just the conclusion. Silence on irrelevant cases is preferred - they should not appear in the output at all."""

            llm_result = self.llm.invoke(
                [
                    {"role": "system", "content": system_prompt},
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
            
            # Clean the markdown to remove any notes about irrelevant cases
            cleaned_markdown = self._clean_irrelevant_case_notes(
                llm_result.analysis_markdown or "# Case Analysis\n\nNo synthesis generated."
            )
            
            result = CaseSynthesisResult(
                analysis_markdown=cleaned_markdown,
                relevant_pdf_paths=filtered_paths,
            )
            logger.info(f"LLM synthesis successful: {len(result.analysis_markdown)} chars markdown (after cleaning), {len(result.relevant_pdf_paths)} PDFs")
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

    def _clean_irrelevant_case_notes(self, markdown: str) -> str:
        """
        Remove any notes or mentions of irrelevant cases from markdown output.
        
        Strips out:
        - "Note: ... is not relevant" sections
        - "Note: ... is tangential" sections
        - "Conclusion" sections that mention irrelevance
        - Any section after a "## Note" or "## Notes" header that discusses exclusions
        
        Args:
            markdown: Raw markdown from LLM
            
        Returns:
            Cleaned markdown with irrelevance notes removed
        """
        import re
        
        # Remove "## Note" or "## Notes" sections that discuss irrelevance/tangentiality
        # Pattern matches ## Note(s) followed by content mentioning "not relevant", "tangential", "not directly relevant", etc.
        patterns_to_remove = [
            # Remove Note sections discussing irrelevance
            r"##\s*Note[s]?:?\s*\n.*?(?:not.*?relevant|tangential|not.*?directly.*?related|peripheral).*?(?=##\s*[A-Z]|$)",
            # Remove conclusion sections mentioning specific irrelevant cases
            r"(Conclusion|CONCLUSION)\n.*?(?:not.*?relevant|tangential|not.*?directly.*?related).*?(?=##|$)",
            # Remove inline note patterns like "Note: The second case provided... is not directly relevant"
            r"\n*Note:\s+The\s+(?:second|third|first|another)\s+case.*?(?:not\s+directly\s+relevant|tangential).*?(?=\n\n|##|$)",
            # Remove "is not directly relevant to" patterns
            r"is\s+not\s+directly\s+relevant\s+to.*?(?=\n\n|##|$)",
            # Remove sections explicitly stating cases should be ignored
            r"(?:should\s+be\s+)?ignored.*?(?=\n\n|##|$)",
        ]
        
        cleaned = markdown
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove excessive newlines
        cleaned = re.sub(r"\n\n\n+", "\n\n", cleaned)
        cleaned = cleaned.strip()
        
        return cleaned
