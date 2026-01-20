import sys
import os
from typing import Dict, Any

# Add project root to path
sys.path.append(os.getcwd())

from src.models import GraphState, OrchestratorPlan, NextModule, AgentType
from src.workflows.chat.builder import build_graph

def run_test(query: str, domain: str, expected_node: str):
    print(f"\n🧪 Testing Query: '{query}' (Domain: {domain})")
    print("-" * 50)
    
    workflow = build_graph()
    
    # Mock state at Orchestrator output
    mock_plan = OrchestratorPlan(
        next_module=NextModule(agent_number=2, reasoning="Test"), # 2 = Procedural Guidance
        legal_domain=domain
    )
    
    # We want to verify routing, but LangGraph 'invoke' runs the whole graph.
    # To test routing specifically, we can inspect the graph or run it with a mock state 
    # positioned *after* orchestrator if possible, OR just run the graph and see which nodes trigger.
    # But since we don't have real LLMs mocked easily here, running the full graph might be slow/costly.
    
    # Alternative: Test the routing function directly.
    from src.workflows.chat.builder import route_from_orchestrator
    
    state = {
        "orchestrator_plan": mock_plan.dict(),
        "pending_clarification": None
    }
    
    result = route_from_orchestrator(state)
    print(f"   Route Result: {result}")
    
    if result == expected_node:
        print("   ✅ PASS")
    elif isinstance(expected_node, list) and sorted(result) == sorted(expected_node):
        print("   ✅ PASS") 
    else:
        print(f"   ❌ FAIL (Expected {expected_node}, got {result})")

if __name__ == "__main__":
    run_test("Property dispute", "civil", "procedural_guidance_civil")
    run_test("Theft case", "criminal", "procedural_guidance_criminal")
    run_test("Assault and Eviction", "both", ["procedural_guidance_civil", "procedural_guidance_criminal"])
