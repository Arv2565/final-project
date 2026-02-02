#!/usr/bin/env python3
"""
Example script to test the legal query processing LangGraph flow.

This demonstrates the new QueryRouterAgent → IntentClassifierAgent pipeline.
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.workflows.chat import build_graph


def test_query(graph, query: str, description: str):
    """Test a single query through the graph."""
    print(f"\n{'='*80}")
    print(f"TEST: {description}")
    print(f"{'='*80}")
    print(f"Input Query: {query}\n")
    
    # Invoke the graph
    result = graph.invoke({"user_query": query})
    
    # Extract outputs
    router_output = result.get("router_output")
    classifier_output = result.get("classifier_output")
    
    # Display router output
    print("=" * 40)
    print("QUERY ROUTER OUTPUT")
    print("=" * 40)
    if router_output:
        print(f"Cleaned Query: {router_output.cleaned_query}")
        print(f"Language: {router_output.metadata.language}")
        print(f"Has Personal Data: {router_output.metadata.has_personal_data}")
        print(f"Is Legal Question: {router_output.metadata.is_legal_question}")
    else:
        print("No router output")
    
    # Display classifier output
    print("\n" + "=" * 40)
    print("INTENT CLASSIFIER OUTPUT")
    print("=" * 40)
    if classifier_output:
        print(f"Intent: {classifier_output.intent.value}")
        print(f"Jurisdiction: {classifier_output.entities.jurisdiction}")
        print(f"Topic: {classifier_output.entities.topic}")
        print(f"Time Frame: {classifier_output.entities.time_frame}")
    else:
        print("No classifier output")
    
    # Display raw state for debugging
    print("\n" + "=" * 40)
    print("RAW STATE (for debugging)")
    print("=" * 40)
    print(json.dumps({
        "user_query": result.get("user_query"),
        "router_output": {
            "cleaned_query": router_output.cleaned_query if router_output else None,
            "metadata": {
                "language": router_output.metadata.language if router_output else None,
                "has_personal_data": router_output.metadata.has_personal_data if router_output else None,
                "is_legal_question": router_output.metadata.is_legal_question if router_output else None,
            }
        } if router_output else None,
        "classifier_output": {
            "intent": classifier_output.intent.value if classifier_output else None,
            "entities": {
                "jurisdiction": classifier_output.entities.jurisdiction if classifier_output else None,
                "topic": classifier_output.entities.topic if classifier_output else None,
                "time_frame": classifier_output.entities.time_frame if classifier_output else None,
            }
        } if classifier_output else None,
    }, indent=2))


def main():
    """Run test cases for the legal query processing flow."""
    print("\n" + "🔬 Legal Query Processing Flow - Test Cases")
    print("=" * 80)
    
    # Build the graph once
    graph = build_graph()
    
    # Test Case 1: English legal query (procedure)
    test_query(
        graph,
        "How do I file for divorce in India?",
        "English Legal Query - Procedure"
    )
    
    # Test Case 2: Non-English query (Hindi)
    test_query(
        graph,
        "भारत में तलाक के लिए कैसे आवेदन करें?",
        "Hindi Legal Query - Should translate to English"
    )
    
    # Test Case 3: Law explanation query
    test_query(
        graph,
        "What is Section 420 of the Indian Penal Code?",
        "Law Explanation Query"
    )
    
    # Test Case 4: General question
    test_query(
        graph,
        "What is the weather like today?",
        "General Non-Legal Question"
    )
    
    # Test Case 5: Chit-chat
    test_query(
        graph,
        "Hello! How are you doing?",
        "Casual Chit-Chat"
    )
    
    # Test Case 6: Query with personal data
    test_query(
        graph,
        "My name is John Doe and I live at 123 Main Street. Can I sue my neighbor for property damage?",
        "Query with Personal Information"
    )
    
    # Test Case 7: Case reference query
    test_query(
        graph,
        "Tell me about the Kesavananda Bharati case",
        "Case Reference Query"
    )
    
    print("\n" + "=" * 80)
    print("✅ All test cases completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
