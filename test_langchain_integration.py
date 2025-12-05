#!/usr/bin/env python3
"""
Test script to verify LangChain with_structured_output() integration.
Tests QueryRouterAgent and IntentClassifierAgent with the new implementation.
"""

import sys
from typing import Dict, Any

# Test imports
try:
    from src.agents.query_router_agent import QueryRouterAgent
    from src.agents.intent_classifier_agent import IntentClassifierAgent
    from src.models import GraphState, QueryRouterOutput, IntentClassifierOutput
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 1: QueryRouterAgent initialization
print("\n[Test 1] QueryRouterAgent initialization")
try:
    router_agent = QueryRouterAgent()
    assert hasattr(router_agent, 'llm'), "Agent should have 'llm' attribute"
    print("✓ QueryRouterAgent initialized successfully with ChatOpenAI")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Test 2: IntentClassifierAgent initialization
print("\n[Test 2] IntentClassifierAgent initialization")
try:
    classifier_agent = IntentClassifierAgent()
    assert hasattr(classifier_agent, 'llm'), "Agent should have 'llm' attribute"
    print("✓ IntentClassifierAgent initialized successfully with ChatOpenAI")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Test 3: QueryRouterAgent invocation
print("\n[Test 3] QueryRouterAgent invocation")
try:
    test_state: GraphState = {"user_query": "What is the procedure for divorce in India?"}
    result = router_agent(test_state)
    
    assert "router_output" in result, "Result should contain 'router_output' key"
    router_output = result["router_output"]
    
    assert isinstance(router_output, QueryRouterOutput), f"Expected QueryRouterOutput, got {type(router_output)}"
    assert hasattr(router_output, "cleaned_query"), "QueryRouterOutput should have 'cleaned_query'"
    assert hasattr(router_output, "metadata"), "QueryRouterOutput should have 'metadata'"
    
    print(f"✓ QueryRouterAgent returned valid structured output")
    print(f"  - cleaned_query: {router_output.cleaned_query}")
    print(f"  - language: {router_output.metadata.language}")
    print(f"  - is_legal_question: {router_output.metadata.is_legal_question}")
except Exception as e:
    print(f"✗ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: IntentClassifierAgent invocation
print("\n[Test 4] IntentClassifierAgent invocation")
try:
    state_with_router_output = {
        "user_query": "What is the procedure for divorce in India?",
        "router_output": router_output
    }
    result = classifier_agent(state_with_router_output)
    
    assert "classifier_output" in result, "Result should contain 'classifier_output' key"
    classifier_output = result["classifier_output"]
    
    assert isinstance(classifier_output, IntentClassifierOutput), f"Expected IntentClassifierOutput, got {type(classifier_output)}"
    assert hasattr(classifier_output, "intent"), "IntentClassifierOutput should have 'intent'"
    assert hasattr(classifier_output, "entities"), "IntentClassifierOutput should have 'entities'"
    
    print(f"✓ IntentClassifierAgent returned valid structured output")
    print(f"  - intent: {classifier_output.intent}")
    print(f"  - jurisdiction: {classifier_output.entities.jurisdiction}")
    print(f"  - topic: {classifier_output.entities.topic}")
except Exception as e:
    print(f"✗ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Error handling - missing user_query
print("\n[Test 5] Error handling - missing user_query")
try:
    bad_state: GraphState = {}
    result = router_agent(bad_state)
    print("✗ Should have raised ValueError for missing user_query")
    sys.exit(1)
except ValueError as e:
    print(f"✓ Correctly raised ValueError: {e}")
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    sys.exit(1)

# Test 6: Error handling - missing router_output
print("\n[Test 6] Error handling - missing router_output")
try:
    bad_state: GraphState = {"user_query": "test"}
    result = classifier_agent(bad_state)
    print("✗ Should have raised ValueError for missing router_output")
    sys.exit(1)
except ValueError as e:
    print(f"✓ Correctly raised ValueError: {e}")
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("✓ All tests passed! LangChain integration successful.")
print("="*60)
