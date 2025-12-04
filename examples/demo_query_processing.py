#!/usr/bin/env python3
"""
Simple example demonstrating how to use the legal query processing graph.

Usage:
    python examples/demo_query_processing.py "Your legal question here"
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.workflows.chat import build_graph


def process_query(query: str):
    """Process a single legal query through the pipeline."""
    # Build the graph
    graph = build_graph()
    
    # Invoke with user query
    result = graph.invoke({"user_query": query})
    
    # Extract structured outputs
    router_output = result.get("router_output")
    classifier_output = result.get("classifier_output")
    
    # Display results
    print("\n" + "="*60)
    print("QUERY PROCESSING RESULTS")
    print("="*60)
    
    print(f"\n📝 Original Query:")
    print(f"   {query}")
    
    if router_output:
        print(f"\n🔄 Cleaned Query:")
        print(f"   {router_output.cleaned_query}")
        
        print(f"\n🌍 Language: {router_output.metadata.language or 'Unknown'}")
        print(f"⚖️  Legal Question: {'Yes' if router_output.metadata.is_legal_question else 'No'}")
        print(f"🔒 Has Personal Data: {'Yes' if router_output.metadata.has_personal_data else 'No'}")
    
    if classifier_output:
        print(f"\n🎯 Intent: {classifier_output.intent.value}")
        print(f"📍 Jurisdiction: {classifier_output.entities.jurisdiction or 'Not specified'}")
        print(f"📚 Topic: {classifier_output.entities.topic or 'Not specified'}")
        print(f"⏰ Time Frame: {classifier_output.entities.time_frame or 'Not specified'}")
    
    # Show JSON export option
    print(f"\n📤 JSON Export:")
    print(json.dumps({
        "query": query,
        "cleaned_query": router_output.cleaned_query if router_output else None,
        "language": router_output.metadata.language if router_output else None,
        "intent": classifier_output.intent.value if classifier_output else None,
        "jurisdiction": classifier_output.entities.jurisdiction if classifier_output else None,
        "topic": classifier_output.entities.topic if classifier_output else None,
    }, indent=2))
    
    print("\n" + "="*60)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python demo_query_processing.py 'Your question here'")
        print("\nExample queries:")
        print("  - 'How do I file for divorce in India?'")
        print("  - 'What is Section 420 of IPC?'")
        print("  - 'भारत में तलाक कैसे लें?'")
        return 1
    
    query = " ".join(sys.argv[1:])
    
    try:
        process_query(query)
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure OPENAI_API_KEY is set in your .env file")
        return 1


if __name__ == "__main__":
    exit(main())
