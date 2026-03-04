"""
Case Retriever Module - 3-Agent System for Case Law Discovery.

Agents:
- LowerCourtCaseFinderAgent: Find cases from district/lower courts
- UpperCourtCaseFinderAgent: Find precedents from Supreme/High courts
- CaseComparativeAnalyzerAgent: Synthesize and analyze both

Workflow:
- Executes lower and upper court finders in parallel
- Synthesizes results into comprehensive case analysis
- Detects reversals, appellate chains, and legal principles
"""

from .models import (
    CaseInfo,
    LowerCourtCaseResult,
    UpperCourtCaseResult,
    CaseAnalysisResult,
    CaseRetrieverState,
    QueryContext,
    PrecedentInfo,
    AppellateChainLink,
)

from .lower_court_finder import LowerCourtCaseFinderAgent
from .upper_court_finder import UpperCourtCaseFinderAgent
from .comparative_analyzer import CaseComparativeAnalyzerAgent
from .workflow import CaseRetrieverWorkflow

__all__ = [
    "CaseInfo",
    "LowerCourtCaseResult",
    "UpperCourtCaseResult",
    "CaseAnalysisResult",
    "CaseRetrieverState",
    "QueryContext",
    "PrecedentInfo",
    "AppellateChainLink",
    "LowerCourtCaseFinderAgent",
    "UpperCourtCaseFinderAgent",
    "CaseComparativeAnalyzerAgent",
    "CaseRetrieverWorkflow",
]
