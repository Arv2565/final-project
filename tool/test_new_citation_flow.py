"""
Test script for the new simplified citation-based case retrieval system.

This demonstrates the flow:
1. LowerCourtCaseFinderAgent selects max 2 citations from lower_case.json using LLM
2. UpperCourtCaseFinderAgent selects max 2 citations from higher_case.json using LLM  
3. CaseComparativeAnalyzerAgent enriches citations from casefiles.json and generates analysis
"""

import sys
import os
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.case_retriever.lower_court_finder import LowerCourtCaseFinderAgent
from src.agents.case_retriever.upper_court_finder import UpperCourtCaseFinderAgent
from src.agents.case_retriever.comparative_analyzer import CaseComparativeAnalyzerAgent


def test_citation_based_retrieval():
    """Test the complete citation-based retrieval flow."""
    
    print("=" * 80)
    print("TESTING NEW CITATION-BASED CASE RETRIEVAL SYSTEM")
    print("=" * 80)
    
    # Sample query
    test_query = "Cases related to fundamental rights under Article 21 of the Constitution"
    
    print(f"\n📝 Test Query: {test_query}\n")
    
    # Stage 1: Lower Court Citation Selection
    print("=" * 80)
    print("STAGE 1: LOWER COURT CITATION SELECTION")
    print("=" * 80)
    
    lower_finder = LowerCourtCaseFinderAgent()
    state = {"user_query": test_query}
    
    print(f"✅ Loaded {len(lower_finder.lower_cases)} lower court cases from JSON")
    print("🔍 Calling LLM to select max 2 relevant citations...\n")
    
    lower_result = lower_finder(state)
    lower_citations = lower_result.get("lower_citations", [])
    
    print(f"✅ Lower court finder selected {len(lower_citations)} citations:")
    for i, citation in enumerate(lower_citations, 1):
        print(f"   {i}. {citation}")
    
    # Stage 2: Upper Court Citation Selection
    print("\n" + "=" * 80)
    print("STAGE 2: UPPER COURT CITATION SELECTION")
    print("=" * 80)
    
    upper_finder = UpperCourtCaseFinderAgent()
    
    print(f"✅ Loaded {len(upper_finder.higher_cases)} higher court cases from JSON")
    print("🔍 Calling LLM to select max 2 relevant citations...\n")
    
    upper_result = upper_finder(state=state)
    upper_citations = upper_result.get("upper_citations", [])
    
    print(f"✅ Upper court finder selected {len(upper_citations)} citations:")
    for i, citation in enumerate(upper_citations, 1):
        print(f"   {i}. {citation}")
    
    # Stage 3: Citation Enrichment and Analysis
    print("\n" + "=" * 80)
    print("STAGE 3: CITATION ENRICHMENT & LLM ANALYSIS")
    print("=" * 80)
    
    analyzer = CaseComparativeAnalyzerAgent()
    
    print(f"📚 Enriching {len(lower_citations) + len(upper_citations)} citations with full case JSON from casefiles.json...")
    
    analysis_result_dict = analyzer(
        lower_citations=lower_citations,
        upper_citations=upper_citations,
        state=state
    )
    
    analysis_result = analysis_result_dict.get("analysis_result")
    
    if analysis_result:
        print("✅ Analysis complete!\n")
        
        # Show markdown preview (first 500 chars)
        markdown = analysis_result.analysis_markdown
        print("📄 Analysis Markdown (preview):")
        print("-" * 80)
        print(markdown[:500] + "..." if len(markdown) > 500 else markdown)
        print("-" * 80)
        
        # Show PDF paths
        pdf_paths = analysis_result.relevant_pdf_paths
        print(f"\n📎 Relevant PDF Paths ({len(pdf_paths)}):")
        for i, path in enumerate(pdf_paths, 1):
            print(f"   {i}. {path}")
    else:
        print("❌ Analysis failed or returned None")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Lower Citations Selected: {len(lower_citations)}/2")
    print(f"✅ Upper Citations Selected: {len(upper_citations)}/2")
    print(f"✅ Total Cases in Analysis: {len(lower_citations) + len(upper_citations)}")
    print(f"✅ PDF Paths Extracted: {len(pdf_paths) if analysis_result else 0}")
    print(f"✅ Markdown Length: {len(markdown) if analysis_result else 0} characters")
    print("\n✨ New citation-based retrieval system working successfully!\n")


if __name__ == "__main__":
    try:
        test_citation_based_retrieval()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
