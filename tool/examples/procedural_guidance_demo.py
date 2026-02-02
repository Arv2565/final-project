#!/usr/bin/env python3
"""Demo script for Procedural Guidance Module.

Tests the 4-agent procedural guidance workflow with various queries.
"""

import sys
import os
import json
from pprint import pprint

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.workflows.chat.builder import build_graph
from src.models import GraphState


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_procedural_output(state: GraphState):
    """Print structured procedural guidance output."""
    procedural_state = state.get("procedural_guidance_state")
    
    if not procedural_state:
        print("⚠️  No procedural guidance state found")
        return
    
    # Timeline Constraints
    if procedural_state.timeline_constraints and procedural_state.timeline_constraints.constraints:
        print_section("⏰ TIMELINE CONSTRAINTS")
        for constraint in procedural_state.timeline_constraints.constraints:
            print(f"\n📌 {constraint.constraint_type.upper()}")
            print(f"   Description: {constraint.description}")
            print(f"   Time Limit: {constraint.time_limit}")
            print(f"   Reference: {constraint.statutory_reference}")
            print(f"   Consequences: {constraint.consequences}")
    
    # Checklist
    if procedural_state.checklist and procedural_state.checklist.items:
        print_section("📋 PREPARATION CHECKLIST")
        high_items = [item for item in procedural_state.checklist.items if item.priority == "high"]
        medium_items = [item for item in procedural_state.checklist.items if item.priority == "medium"]
        low_items = [item for item in procedural_state.checklist.items if item.priority == "low"]
        
        if high_items:
            print("\n🔴 HIGH PRIORITY:")
            for item in high_items:
                print(f"   • {item.description}")
                print(f"     Reason: {item.reason}")
                print(f"     Legal Basis: {item.statutory_basis}")
        
        if medium_items:
            print("\n🟡 MEDIUM PRIORITY:")
            for item in medium_items:
                print(f"   • {item.description}")
        
        if low_items:
            print("\n🟢 LOW PRIORITY:")
            for item in low_items:
                print(f"   • {item.description}")
    
    # Actor Mapping
    if procedural_state.actor_mapping and procedural_state.actor_mapping.actor_mappings:
        print_section("👥 RESPONSIBLE ACTORS")
        for mapping in procedural_state.actor_mapping.actor_mappings:
            print(f"\n🎯 {mapping.step}")
            print(f"   Party: {mapping.responsible_party}")
            if mapping.responsible_officer:
                print(f"   Officer: {mapping.responsible_officer}")
            print(f"   Contact: {mapping.contact_info}")
            print(f"   Reference: {mapping.statutory_reference}")
    
    # Estimated Effort & Ordered Steps
    if procedural_state.estimated_effort:
        print_section("📊 PROCEDURAL STEPS & ESTIMATES")
        effort = procedural_state.estimated_effort
        
        print(f"\n⏱️  Total Time: {effort.total_estimated_time}")
        print(f"💰 Total Cost: {effort.total_estimated_cost}\n")
        
        for step in effort.ordered_steps:
            print(f"\n{'─' * 60}")
            print(f"STEP {step.step_number}: {step.action}")
            print(f"{'─' * 60}")
            print(f"Responsible: {', '.join(step.responsible_actors)}")
            print(f"Time: {step.estimated_time}")
            print(f"Cost: {step.estimated_cost}")
            
            if step.required_documents:
                print(f"Documents: {', '.join(step.required_documents)}")
            
            if step.forms:
                print(f"Forms: {', '.join(step.forms)}")
            
            if step.contact_points:
                print(f"Contact: {', '.join(step.contact_points)}")
            
            print(f"Legal Ref: {step.statutory_reference}")


def test_query(graph, query: str):
    """Test a single query through the workflow."""
    print_section(f"🔍 TESTING QUERY: {query}")
    
    initial_state = GraphState(user_query=query)
    
    try:
        # Run the workflow
        final_state = graph.invoke(initial_state)
        
        # Check which module was selected
        orchestrator_plan = final_state.get("orchestrator_plan")
        if orchestrator_plan and isinstance(orchestrator_plan, dict):
            next_module = orchestrator_plan.get("next_module", {})
            agent_number = next_module.get("agent_number")
            reasoning = next_module.get("reasoning")
            
            print(f"\n🎯 Orchestrator Decision:")
            print(f"   Selected Agent: {agent_number}")
            print(f"   Reasoning: {reasoning}")
        
        # If procedural guidance was selected, print output
        if agent_number == 2:
            print_procedural_output(final_state)
        else:
            print(f"\n⚠️  Query routed to agent {agent_number}, not procedural guidance")
        
        return final_state
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run demo tests for procedural guidance module."""
    print_section("🚀 PROCEDURAL GUIDANCE MODULE DEMO")
    print("Testing BNSS and Evidence Act compliance\n")
    
    # Build the workflow graph
    print("Building workflow graph...")
    graph = build_graph()
    print("✅ Graph built successfully\n")
    
    # Test queries that should route to procedural guidance (agent 2)
    test_queries = [
        "How do I file an FIR for theft?",
        "What is the process to apply for bail in a criminal case?",
        "How to file an appeal in a criminal case?",
        "What are the steps to file a complaint under BNSS?",
        "How long do I have to file an appeal after conviction?",
    ]
    
    for query in test_queries:
        test_query(graph, query)
        print("\n" + "=" * 80 + "\n")
        input("Press Enter to continue to next query...")
    
    print_section("✅ DEMO COMPLETED")


if __name__ == "__main__":
    main()
