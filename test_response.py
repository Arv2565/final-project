#!/usr/bin/env python3
"""Quick test to see final response output."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.workflows.chat.builder import build_graph
from src.models import GraphState

# Build graph
graph = build_graph()

# Test query
query = "How do I file an FIR for theft of my mobile phone?"
initial_state = GraphState(user_query=query)

# Run workflow
final_state = graph.invoke(initial_state)

# Print final response
print("\n" + "="*80)
print("FINAL RESPONSE TO USER")
print("="*80)
print(final_state.get("final_response", "No final response generated"))
print("\n")
