"""
Case Comparative Analyzer Agent for Case Retrieval Module.

This agent synthesizes results from lower and upper court finders,
performs comparative analysis, and generates final recommendations.
"""

import logging
from typing import List, Dict, Any, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.agents.case_retriever.models import (
    CaseAnalysisResult, CommonStatuteInfo, PrecedentInfo, LowerCourtCaseResult,
    UpperCourtCaseResult, CaseInfo
)

logger = logging.getLogger(__name__)


class CaseComparativeAnalyzerAgent:
    """Synthesizes case retrieval results from both court levels."""
    
    def __call__(
        self,
        lower_result: LowerCourtCaseResult,
        upper_result: UpperCourtCaseResult,
        state: Optional[Dict[str, Any]] = None,
        callbacks: Optional[List] = None
    ) -> Dict[str, Any]:
        """
        Execute comparative analysis on case results.
        
        Args:
            lower_result: LowerCourtCaseResult from lower court finder
            upper_result: UpperCourtCaseResult from upper court finder
            state: GraphState
            callbacks: Optional callbacks
        
        Returns:
            Dict with 'analysis_result' key containing CaseAnalysisResult
        """
        try:
            logger.info(
                f"CaseComparativeAnalyzer: Analyzing "
                f"{len(lower_result.cases)} lower cases, "
                f"{len(upper_result.precedents)} precedents"
            )
            
            # Perform comparative analyses
            common_statutes = self._extract_common_statutes(lower_result, upper_result)
            reversals = self._identify_reversals(lower_result, upper_result)
            principles = self._derive_legal_principles(lower_result, upper_result)
            summary = self._generate_summary(lower_result, upper_result, reversals, principles)
            recommendations = self._generate_recommendations(lower_result, upper_result, reversals)
            
            # Compute overall confidence
            confidence = self._compute_confidence(lower_result, upper_result)
            
            analysis_result = CaseAnalysisResult(
                summary=summary,
                lower_court_cases=lower_result.cases,
                precedents=upper_result.precedents,
                common_statutes=common_statutes,
                appellate_chains=upper_result.appellate_chains,
                reversals_identified=reversals,
                legal_principles_derived=principles,
                confidence_score=confidence,
                recommendations=recommendations
            )
            
            logger.info(
                f"CaseComparativeAnalyzer: Analysis complete. "
                f"Found {len(reversals)} reversals, {len(principles)} principles"
            )
            
            return {"analysis_result": analysis_result}
        
        except Exception as e:
            logger.error(f"CaseComparativeAnalyzer error: {e}")
            raise RuntimeError(f"Comparative analysis failed: {e}")
    
    def _extract_common_statutes(
        self,
        lower_result: LowerCourtCaseResult,
        upper_result: UpperCourtCaseResult
    ) -> List[CommonStatuteInfo]:
        """Extract statutes mentioned across both court levels."""
        statute_counts: Dict[str, List[str]] = {}
        statute_interpretations: Dict[str, List[str]] = {}
        
        # Collect from lower court cases
        for case in lower_result.cases:
            for statute in case.statutes_mentioned or []:
                if statute not in statute_counts:
                    statute_counts[statute] = []
                    statute_interpretations[statute] = []
                statute_counts[statute].append(case.citation)
        
        # Collect from precedents
        for precedent in upper_result.precedents:
            # Would need to extract from precedent details in production
            pass
        
        # Build CommonStatuteInfo list
        common_statutes = []
        for statute_name, case_citations in statute_counts.items():
            if len(case_citations) > 1 or statute_name in statute_interpretations:
                common_statutes.append(CommonStatuteInfo(
                    statute_name=statute_name,
                    section="",  # Would be extracted from case details
                    frequency=len(case_citations),
                    interpretations=statute_interpretations.get(statute_name, []),
                    case_citations=case_citations
                ))
        
        return sorted(common_statutes, key=lambda x: x.frequency, reverse=True)
    
    def _identify_reversals(
        self,
        lower_result: LowerCourtCaseResult,
        upper_result: UpperCourtCaseResult
    ) -> List[Dict[str, Any]]:
        """Identify cases where lower court decision was overturned."""
        reversals = []
        
        # Find precedents with REVERSED status
        for precedent in upper_result.precedents:
            if precedent.reversal_status == "REVERSED":
                # Attempt to match with lower court case
                matching_lower = self._find_related_lower_case(
                    precedent, lower_result.cases
                )
                
                if matching_lower:
                    reversals.append({
                        "lower_case": matching_lower.dict(),
                        "upper_precedent": precedent.dict(),
                        "reversal_status": "CONFIRMED",
                        "reversal_reason": self._extract_reversal_reason(precedent)
                    })
                else:
                    # Standalone reversal for reference
                    reversals.append({
                        "lower_case": None,
                        "upper_precedent": precedent.dict(),
                        "reversal_status": "REFERENCE",
                        "reversal_reason": "Precedent shows reversal pattern"
                    })
        
        return reversals
    
    def _find_related_lower_case(
        self,
        precedent: PrecedentInfo,
        lower_cases: List[CaseInfo]
    ) -> Optional[CaseInfo]:
        """Attempt to find lower court case related to precedent."""
        # Simple matching - could be enhanced with NLP
        for case in lower_cases:
            # Check for same parties (simplified)
            if any(word in precedent.citation.lower() for word in case.citation.lower().split()):
                return case
        
        return None
    
    def _extract_reversal_reason(self, precedent: PrecedentInfo) -> str:
        """Extract reason for reversal from precedent."""
        # Simplified - would extract from full judgment text in production
        return "Court found procedural or substantive error in lower court decision"
    
    def _derive_legal_principles(
        self,
        lower_result: LowerCourtCaseResult,
        upper_result: UpperCourtCaseResult
    ) -> List[str]:
        """Derive key legal principles from case analysis."""
        principles = []
        
        # Extract from common concepts
        all_concepts = set()
        for case in lower_result.cases:
            all_concepts.update(case.legal_concepts or [])
        
        for precedent in upper_result.precedents:
            all_concepts.update(precedent.common_concepts or [])
        
        # Convert concepts to principles
        concept_to_principle = {
            "personal_liberty": "Right to personal liberty is fundamental and must be protected",
            "habeas_corpus": "Habeas corpus remedies arbitrary detention",
            "reasonable_accommodation": "Government must provide reasonable accommodation for disabilities",
            "proportionality": "Punishment must be proportionate to the offence",
            "natural_justice": "Both parties must get fair hearing and opportunity to defend",
            "precedent": "Lower courts must follow precedents from higher courts",
            "statutory_interpretation": "Statutes must be interpreted harmoniously with Constitution"
        }
        
        for concept in all_concepts:
            if concept in concept_to_principle:
                principles.append(concept_to_principle[concept])
        
        return list(set(principles))  # Remove duplicates
    
    def _generate_summary(
        self,
        lower_result: LowerCourtCaseResult,
        upper_result: UpperCourtCaseResult,
        reversals: List[Dict[str, Any]],
        principles: List[str]
    ) -> str:
        """Generate narrative summary of analysis."""
        summary_parts = []
        
        summary_parts.append(f"Analysis found {len(lower_result.cases)} relevant lower court cases.")
        
        if len(upper_result.precedents) > 0:
            summary_parts.append(
                f"At the appellate level, {len(upper_result.precedents)} precedents provide guidance, "
                f"with {upper_result.reversals_detected} cases involving reversals."
            )
        
        if reversals:
            summary_parts.append(
                f"Notably, {len(reversals)} cases show reversal patterns that may be relevant to the query."
            )
        
        if principles:
            summary_parts.append(
                f"The cases consistently apply {len(principles)} key legal principles: "
                f"{', '.join(principles[:3])}{'...' if len(principles) > 3 else ''}."
            )
        
        if upper_result.appellate_chains:
            summary_parts.append(
                f"{len(upper_result.appellate_chains)} complete appellate chains were identified, "
                f"showing progression through multiple court levels."
            )
        
        common_statutes = self._extract_common_statutes(lower_result, upper_result)
        if common_statutes:
            summary_parts.append(
                f"Key statutes include {common_statutes[0].statute_name}"
                f"{'and others' if len(common_statutes) > 1 else ''}, "
                f"interpreted across {len(common_statutes)} cases."
            )
        
        return " ".join(summary_parts)
    
    def _generate_recommendations(
        self,
        lower_result: LowerCourtCaseResult,
        upper_result: UpperCourtCaseResult,
        reversals: List[Dict[str, Any]]
    ) -> str:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Recommendation based on case strength
        avg_score = sum(
            (c.similarity_score or 0.5) for c in lower_result.cases
        ) / len(lower_result.cases) if lower_result.cases else 0
        
        if avg_score > 0.8:
            recommendations.append(
                "Strong case precedents found. Recommend citing primary lower court cases directly."
            )
        elif avg_score > 0.6:
            recommendations.append(
                "Moderate precedent strength. Consider combining multiple related cases."
            )
        else:
            recommendations.append(
                "Limited direct precedents. Focus on statutory interpretation from upper courts."
            )
        
        # Recommendation based on reversals
        if reversals:
            recommendations.append(
                "Reversal cases identified. Carefully review these to understand what arguments failed."
            )
        
        # Recommendation based on precedent availability
        if not upper_result.precedents:
            recommendations.append(
                "Few upper court precedents found. Consider consulting legal commentary."
            )
        elif upper_result.reversals_detected > 0:
            recommendations.append(
                "Multiple precedent inversals detected. Prepare counter-arguments carefully."
            )
        else:
            recommendations.append(
                "Consistent precedent line found. This strengthens the case."
            )
        
        return " ".join(recommendations)
    
    def _compute_confidence(
        self,
        lower_result: LowerCourtCaseResult,
        upper_result: UpperCourtCaseResult
    ) -> float:
        """Compute overall confidence score."""
        confidence = 0.5  # Base score
        
        # Increase with number of cases
        if len(lower_result.cases) > 5:
            confidence += 0.2
        elif len(lower_result.cases) > 0:
            confidence += 0.1
        
        # Increase with precedent support
        if len(upper_result.precedents) > 5:
            confidence += 0.15
        elif len(upper_result.precedents) > 0:
            confidence += 0.1
        
        # Decrease if reversals detected (uncertainty)
        if upper_result.reversals_detected > 2:
            confidence -= 0.1
        
        # Cap at 1.0
        return min(confidence, 1.0)
