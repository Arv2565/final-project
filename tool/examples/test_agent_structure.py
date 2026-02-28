#!/usr/bin/env python3
"""
Unit tests for the legal query processing LangGraph flow.

Tests the structure and imports without requiring API keys.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_model_imports():
    """Test that all models can be imported."""
    print("✓ Testing model imports...")
    
    from src.models import (
        QueryRouterOutput,
        QueryMetadata,
        IntentClassifierOutput,
        IntentType,
        ExtractedEntities,
        GraphState,
    )
    
    print("  ✓ QueryRouterOutput")
    print("  ✓ QueryMetadata")
    print("  ✓ IntentClassifierOutput")
    print("  ✓ IntentType")
    print("  ✓ ExtractedEntities")
    print("  ✓ GraphState")
    
    return True


def test_model_structure():
    """Test that models have correct structure."""
    print("\n✓ Testing model structure...")
    
    from src.models import (
        QueryRouterOutput,
        QueryMetadata,
        IntentClassifierOutput,
        IntentType,
        ExtractedEntities,
    )
    
    # Test QueryMetadata
    metadata = QueryMetadata(
        original_language="en",
        language="en",
        has_personal_data=False,
        is_legal_question=True
    )
    assert metadata.language == "en"
    assert metadata.original_language == "en"
    print("  ✓ QueryMetadata structure valid")
    
    # Test QueryRouterOutput
    router_output = QueryRouterOutput(
        cleaned_query="How do I file for divorce?",
        metadata=metadata
    )
    assert router_output.cleaned_query == "How do I file for divorce?"
    assert router_output.metadata.language == "en"
    print("  ✓ QueryRouterOutput structure valid")
    
    # Test ExtractedEntities
    entities = ExtractedEntities(
        jurisdiction="India",
        topic="divorce",
        time_frame="unspecified"
    )
    assert entities.jurisdiction == "India"
    print("  ✓ ExtractedEntities structure valid")
    
    # Test IntentType enum
    assert IntentType.ASK_PROCEDURE.value == "ask_procedure"
    assert IntentType.ASK_LAW_EXPLANATION.value == "ask_law_explanation"
    assert IntentType.ASK_CASE_REFERENCE.value == "ask_case_reference"
    assert IntentType.GENERAL_QUESTION.value == "general_question"
    assert IntentType.CHIT_CHAT.value == "chit_chat"
    print("  ✓ IntentType enum valid")
    
    # Test IntentClassifierOutput
    classifier_output = IntentClassifierOutput(
        intent=IntentType.ASK_PROCEDURE,
        entities=entities
    )
    assert classifier_output.intent == IntentType.ASK_PROCEDURE
    assert classifier_output.entities.topic == "divorce"
    print("  ✓ IntentClassifierOutput structure valid")
    
    return True


def test_graph_state():
    """Test GraphState TypedDict structure."""
    print("\n✓ Testing GraphState...")
    
    from src.models import GraphState, QueryRouterOutput, QueryMetadata
    
    # Create a sample state
    state: GraphState = {
        "user_query": "How do I file for divorce in India?"
    }
    
    assert state["user_query"] == "How do I file for divorce in India?"
    
    # Add router_output
    state["router_output"] = QueryRouterOutput(
        cleaned_query="How do I file for divorce in India?",
        metadata=QueryMetadata(
            original_language="en",
            language="en",
            has_personal_data=False,
            is_legal_question=True
        )
    )
    
    assert state["router_output"].cleaned_query == "How do I file for divorce in India?"
    print("  ✓ GraphState structure valid")
    
    return True


def test_agent_imports():
    """Test that agents can be imported (but not instantiated without API keys)."""
    print("\n✓ Testing agent imports...")
    
    from src.agents import QueryRouterAgent, IntentClassifierAgent
    
    print("  ✓ QueryRouterAgent imported")
    print("  ✓ IntentClassifierAgent imported")
    
    return True


def test_prompt_imports():
    """Test that prompts are defined correctly."""
    print("\n✓ Testing prompt imports...")
    
    from src.prompts.query_router_agent import QUERY_ROUTER_SYSTEM_PROMPT
    from src.prompts.intent_classifier_agent import INTENT_CLASSIFIER_SYSTEM_PROMPT
    
    assert isinstance(QUERY_ROUTER_SYSTEM_PROMPT, str)
    assert len(QUERY_ROUTER_SYSTEM_PROMPT) > 0
    assert "JSON" in QUERY_ROUTER_SYSTEM_PROMPT  # Should mention JSON output
    print("  ✓ QUERY_ROUTER_SYSTEM_PROMPT valid")
    
    assert isinstance(INTENT_CLASSIFIER_SYSTEM_PROMPT, str)
    assert len(INTENT_CLASSIFIER_SYSTEM_PROMPT) > 0
    assert "ask_procedure" in INTENT_CLASSIFIER_SYSTEM_PROMPT  # Should list intents
    print("  ✓ INTENT_CLASSIFIER_SYSTEM_PROMPT valid")
    
    return True


def test_node_imports():
    """Test that nodes can be imported."""
    print("\n✓ Testing node imports...")
    
    from src.nodes.query_router_node import query_router_node
    from src.nodes.intent_classifier_node import intent_classifier_node
    
    print("  ✓ query_router_node imported")
    print("  ✓ intent_classifier_node imported")
    
    return True


def test_graph_builder():
    """Test that the graph builder works."""
    print("\n✓ Testing graph builder...")
    
    from src.workflows.chat import build_graph
    
    # This will fail if OPENAI_API_KEY is not set when the graph is actually invoked,
    # but building the graph should work
    graph = build_graph()
    
    assert graph is not None
    print("  ✓ Graph built successfully")
    print("  ✓ Graph is compiled and ready (requires OPENAI_API_KEY to invoke)")
    
    return True


def test_json_structure():
    """Test that models can be serialized to dict (for JSON export)."""
    print("\n✓ Testing JSON serialization...")
    
    from src.models import (
        QueryRouterOutput,
        QueryMetadata,
        IntentClassifierOutput,
        IntentType,
        ExtractedEntities,
    )
    
    # Create full output
    router_output = QueryRouterOutput(
        cleaned_query="How do I file for divorce in India?",
        metadata=QueryMetadata(
            original_language="en",
            language="en",
            has_personal_data=False,
            is_legal_question=True
        )
    )
    
    classifier_output = IntentClassifierOutput(
        intent=IntentType.ASK_PROCEDURE,
        entities=ExtractedEntities(
            jurisdiction="India",
            topic="divorce",
            time_frame="unspecified"
        )
    )
    
    # Convert to dict (Pydantic models support .dict() method)
    router_dict = router_output.model_dump()
    classifier_dict = classifier_output.model_dump()
    
    assert router_dict["cleaned_query"] == "How do I file for divorce in India?"
    assert router_dict["metadata"]["language"] == "en"
    assert classifier_dict["intent"] == "ask_procedure"
    assert classifier_dict["entities"]["jurisdiction"] == "India"
    
    print("  ✓ Models can be serialized to dict")
    print("  ✓ Ready for JSON export")
    
    return True


def main():
    """Run all unit tests."""
    print("\n" + "="*80)
    print("🧪 Legal Query Processing - Unit Tests")
    print("="*80 + "\n")
    
    tests = [
        test_model_imports,
        test_model_structure,
        test_graph_state,
        test_agent_imports,
        test_prompt_imports,
        test_node_imports,
        test_graph_builder,
        test_json_structure,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"\n❌ {test.__name__} failed: {e}")
            failed += 1
    
    print("\n" + "="*80)
    print(f"📊 Results: {passed} passed, {failed} failed")
    print("="*80)
    
    if failed == 0:
        print("\n✅ All tests passed! The refactored agent flow is ready.")
        print("\n📝 To run with real queries, you need to:")
        print("   1. Set OPENAI_API_KEY in your .env file")
        print("   2. Run: python examples/test_legal_query_flow.py")
    else:
        print("\n❌ Some tests failed. Please review the errors above.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
