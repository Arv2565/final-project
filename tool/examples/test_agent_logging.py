#!/usr/bin/env python3
"""
Test script to demonstrate agent logging output.
Shows all 8 agents printing their graph state and processing details.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.workflows.chat import build_graph

print("\n" + "="*80)
print("🚀 AGENT LOGGING DEMONSTRATION")
print("="*80)
print("\nBuilding workflow graph...")

# Build the graph
graph = build_graph()

print("\n✅ Graph built successfully")
print("\nNow running a test query to demonstrate agent logging...")
print("\nEach agent will print its:")
print("  📥 Input State (what it receives)")
print("  ✅ Output (what it produces)")
print("  📤 Return value (what updates the graph state)")

test_query = "What is the legal consequence of cheating under Indian law?"

print("\n" + "="*80)
print(f"PROCESSING QUERY: {test_query}")
print("="*80)

try:
    result = graph.invoke({"user_query": test_query})
    
    print("\n" + "="*80)
    print("✅ WORKFLOW EXECUTION COMPLETED")
    print("="*80)
    
    print("\nFinal Graph State Summary:")
    print("-" * 80)
    
    if result.get("router_output"):
        print("✓ QueryRouter completed")
        
    if result.get("classifier_output"):
        print("✓ IntentClassifier completed")
        
    if result.get("orchestrator_plan"):
        print("✓ Orchestrator completed")
        
    if result.get("activity_law_state"):
        state = result["activity_law_state"]
        print("✓ Activity-to-Law Pipeline executed:")
        if state.get("fact_structuring"):
            print("  ├─ ✓ FactStructuring completed")
        if state.get("statute_matching"):
            print("  ├─ ✓ StatuteMatching completed")
        if state.get("rule_matching"):
            print("  ├─ ✓ RuleMatching completed")
        if state.get("risk_assessment"):
            print("  ├─ ✓ RiskAssessment completed ⭐")
        if state.get("evidence_linking"):
            print("  └─ ✓ EvidenceLinking completed")
    
    print("-" * 80)
    
except Exception as e:
    print(f"\n❌ Error during execution: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("💡 LOGGING TIP:")
print("="*80)
print("""
Each agent logs its processing details as it executes. Watch the terminal
for:

1. Agent Name Header (with emoji for easy identification)
2. Input State - Shows what data the agent receives from graph state
3. Processing - Shows what the agent is doing
4. Output - Shows the structured result from the LLM
5. Return - Shows what key is being updated in the graph state

This helps you understand:
- Data flow through the pipeline
- What each agent produces
- When/why agents fail (with error messages)
- Overall workflow progression
""")
print("="*80)
