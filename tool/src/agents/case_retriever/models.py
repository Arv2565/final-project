"""
Data models for Case Retriever Module agents and state.

Defines Pydantic models for agent outputs and accumulated state.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from dataclasses import dataclass


class CaseInfo(BaseModel):
    """Information about a single case."""
    case_id: str
    citation: str
    court: str
    court_level: int
    date: str
    decision: Optional[str] = None
    parties_appellant: Optional[str] = None
    parties_respondent: Optional[str] = None
    legal_concepts: List[str] = []
    statutes_mentioned: List[str] = []
    content_preview: Optional[str] = None
    similarity_score: Optional[float] = None
    pdf_path: Optional[str] = None
    full_case_json: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Complete case JSON from casefiles.json (only present when retrieved via dual-RAG)"
    )


class LowerCourtCaseResult(BaseModel):
    """Output from LowerCourtCaseFinder agent."""
    cases: List[CaseInfo] = Field(description="List of lower court cases found")
    query_concepts: List[str] = Field(description="Extracted legal concepts from query")
    search_query: str = Field(description="Processed search query")
    retrieval_confidence: float = Field(description="Overall confidence in retrieval (0.0-1.0)")
    total_cases_available: int = Field(description="Total cases considered in search")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Filters used in search")


class PrecedentInfo(BaseModel):
    """Information about a precedent case."""
    citation: str
    court: str
    court_level: int
    date: str
    decision: Optional[str] = None
    reversal_status: Optional[str] = Field(default=None, description="UPHELD, REVERSED, MODIFIED, etc.")
    common_concepts: List[str] = Field(default_factory=list, description="Concepts shared with lower court cases")
    relevance_score: float = Field(description="Relevance to query (0.0-1.0)")
    relationship_type: Optional[str] = Field(default=None, description="cites, follows, distinguishes, etc.")
    pdf_path: Optional[str] = None


class AppellateChainLink(BaseModel):
    """Single link in an appellate chain."""
    case_id: str
    citation: str
    court: str
    court_level: int
    date: str
    reversal_status: Optional[str] = None
    position_in_chain: int = Field(description="Position from bottom (0=first trial, 1=first appeal, etc.)")


class UpperCourtCaseResult(BaseModel):
    """Output from UpperCourtCaseFinder agent."""
    precedents: List[PrecedentInfo] = Field(description="Upper court precedents found")
    appellate_chains: List[List[AppellateChainLink]] = Field(description="Complete appellate chains for discovered chains")
    query_concepts: List[str] = Field(description="Legal concepts from query")
    search_query: str = Field(description="Processed search query")
    retrieval_confidence: float = Field(description="Overall confidence (0.0-1.0)")
    total_precedents_available: int = Field(description="Total precedents considered")
    reversals_detected: int = Field(description="Number of reversal cases found")


class CaseSynthesisResult(BaseModel):
    """Minimal LLM output for case retrieval response."""
    analysis_markdown: str = Field(
        description="Markdown summary with relevant case descriptions and final conclusion"
    )
    relevant_pdf_paths: List[str] = Field(
        default_factory=list,
        description="Relevant PDF paths selected from input cases"
    )


class CaseRetrieverState(BaseModel):
    """Accumulated state for case retriever workflow."""
    user_query: str = Field(description="Original user query")
    case_retriever_state: Dict[str, Any] = Field(default_factory=dict, description="Complete retriever state")
    lower_court_result: Optional[LowerCourtCaseResult] = None
    upper_court_result: Optional[UpperCourtCaseResult] = None
    analysis_result: Optional[CaseSynthesisResult] = None
    workflow_status: str = Field(default="initialized", description="Status: initialized, running, completed, failed")
    error_message: Optional[str] = None


@dataclass
class QueryContext:
    """Context extracted from user query."""
    original_query: str
    legal_concepts: List[str]
    statutes_mentioned: List[str]
    legal_domains: List[str]
    court_levels_preferred: List[int]
    date_constraints: Optional[tuple[str, str]]
    reversal_indicators: bool  # Whether user asks about overturned cases
