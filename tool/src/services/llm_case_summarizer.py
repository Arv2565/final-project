"""
LLM Case Summarizer for Enhanced Vector Retrieval.

Generates semantic case descriptions optimized for vector search,
used to improve retrieval quality in legal case databases.
"""

import logging
from typing import Dict, Any, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.agents.agent_llm_helper import get_agent_llm

logger = logging.getLogger(__name__)


class LLMCaseSummarizer:
    """Generates semantic descriptions for cases using LLM."""
    
    def __init__(self):
        """Initialize with writer model for summarization."""
        self.llm = get_agent_llm(model_type="writer")
    
    def generate_case_description(self, case_data: Dict[str, Any]) -> str:
        """
        Generate a semantic case description optimized for vector search.
        
        Args:
            case_data: Complete case JSON from casefiles.json containing:
                - metadata: citation, court, date, bench, parties_appellant, parties_respondent
                - issues: list of legal issues
                - ratio: reasoning/rationale
                - statutes_interpreted: list of statutes
                - holding: decision and relief
                - legal_concepts: list of applicable concepts
        
        Returns:
            Semantic summary (~250-350 words) capturing:
            - Legal issue and domain
            - Core reasoning and holdings
            - Applicable statutes
            - Key legal concepts
            - Decision and relief
        
        Raises:
            ValueError: If case_data format is invalid
            Exception: If LLM fails
        """
        try:
            # Validate required fields
            metadata = case_data.get("metadata", {})
            citation = metadata.get("citation", "Unknown Case")
            
            # Extract key case components
            issues = case_data.get("issues", [])
            ratio = case_data.get("ratio", {}) or {}
            statutes = case_data.get("statutes_interpreted", [])
            holding = case_data.get("holding", {}) or {}
            legal_concepts = case_data.get("legal_concepts", [])
            
            # Build context for LLM
            case_context = self._build_case_context(
                citation=citation,
                metadata=metadata,
                issues=issues,
                ratio=ratio,
                statutes=statutes,
                holding=holding,
                legal_concepts=legal_concepts
            )
            
            # Create LLM prompt
            prompt = self._create_summarization_prompt(case_context)
            
            # Generate description
            logger.debug(f"Generating description for case: {citation}")
            description = self.llm.invoke(prompt).content
            
            # Validate and clean result
            description = description.strip()
            if not description:
                logger.warning(f"Empty description generated for {citation}, using fallback")
                description = self._generate_fallback_description(case_context)
            
            logger.debug(f"Generated {len(description.split())} word description for {citation}")
            return description
        
        except Exception as e:
            logger.error(f"Error generating case description: {e}")
            raise
    
    def _build_case_context(
        self,
        citation: str,
        metadata: Dict[str, Any],
        issues: list,
        ratio: Dict[str, Any],
        statutes: list,
        holding: Dict[str, Any],
        legal_concepts: list
    ) -> str:
        """Build structured context string for LLM summarization."""
        parts = []
        
        # Citation and court
        court = metadata.get("court", "Unknown Court")
        date = metadata.get("date", "Unknown Date")
        parts.append(f"Case: {citation}")
        parts.append(f"Court: {court}")
        parts.append(f"Date: {date}")
        
        # Issues
        if issues:
            issue_strs = [issue.get("natural_form", "") for issue in issues if issue.get("natural_form")]
            if issue_strs:
                parts.append(f"\nIssues: {'; '.join(issue_strs)}")
        
        # Reasoning/Ratio
        ratio_text = ratio.get("text", "").strip()
        if ratio_text and len(ratio_text) > 50:
            # Truncate to reasonable length for context
            ratio_text = ratio_text[:500] + "..." if len(ratio_text) > 500 else ratio_text
            parts.append(f"\nReasoning: {ratio_text}")
        
        # Statutes
        if statutes:
            statute_strs = [
                f"{s.get('statute_name', '')} ({s.get('section', '')})"
                for s in statutes
                if s.get("statute_name")
            ]
            if statute_strs:
                parts.append(f"\nStatutes Interpreted: {'; '.join(statute_strs)}")
        
        # Holding
        decision = holding.get("decision", "").strip()
        relief = holding.get("relief", "").strip()
        if decision or relief:
            holding_str = decision
            if relief:
                holding_str += f" | Relief: {relief}"
            parts.append(f"\nHolding: {holding_str}")
        
        # Legal concepts
        if legal_concepts:
            concepts_str = ", ".join(legal_concepts[:10])  # Limit to 10 concepts
            parts.append(f"\nKey Legal Concepts: {concepts_str}")
        
        return "\n".join(parts)
    
    def _create_summarization_prompt(self, case_context: str) -> str:
        """Create LLM prompt for case summarization."""
        return f"""You are a legal expert. Create a concise semantic summary of the following legal case optimized for vector search retrieval.

The summary should:
1. Begin with the core legal issue and domain
2. Explain the key reasoning/rationale
3. List applicable statutes and legal concepts
4. State the holding and decision
5. Be 250-350 words
6. Use legal terminology precisely
7. Be written to help find similar precedents

**CASE INFORMATION:**
{case_context}

**YOUR SEMANTIC SUMMARY:**
Generate a comprehensive yet concise semantic summary that captures the legal essence of this case. Focus on what would help find similar cases through legal concept matching."""
    
    def _generate_fallback_description(self, case_context: str) -> str:
        """Generate fallback description if LLM fails."""
        # Simple template-based fallback
        return f"""Legal case summary based on available information:

{case_context}

This case represents an important legal precedent combining the issues, reasoning, statutes, and holding detailed above. The case is relevant for similar issues and legal concepts."""


# Singleton instance for reuse
_summarizer_instance: Optional[LLMCaseSummarizer] = None


def get_case_summarizer() -> LLMCaseSummarizer:
    """Get or create singleton LLM case summarizer instance."""
    global _summarizer_instance
    if _summarizer_instance is None:
        _summarizer_instance = LLMCaseSummarizer()
    return _summarizer_instance
