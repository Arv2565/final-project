# Load environment variables FIRST before any imports
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from src.config.observability import setup_observability
setup_observability()

import argparse
from typing import Dict, Any

from src.workflows.chat import build_graph, GraphState


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Legal Query Processing Graph (Router -> Intent Classifier)."
    )
    parser.add_argument(
        "--question",
        "-q",
        type=str,
        help="User question to pass into the graph. If omitted, you will be prompted.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    question = args.question or input("Enter your question: ").strip()

    if not question:
        raise SystemExit("A question is required to run the graph.")

    initial_state: GraphState = {
        "user_query": question,
    }

    graph = build_graph()

    # Initialize observability callback
    from src.config.observability import get_langfuse_callback
    callback_handler = get_langfuse_callback()
    config = {"callbacks": [callback_handler]} if callback_handler else {}

    # Synchronous invocation loop
    current_state = initial_state
    
    while True:
        final_state: Dict[str, Any] = graph.invoke(current_state, config=config)
        
        # Check for clarification request
        if final_state.get("pending_clarification"):
            clarification = final_state["pending_clarification"]
            
            print("\n" + "="*50)
            print("❓ CLARIFICATION NEEDED")
            print("="*50)
            print(f"System: {clarification['question']}")
            if clarification.get('reason'):
                 print(f"Reason: {clarification['reason']}")
            
            if clarification.get('options'):
                print("Options:")
                for i, opt in enumerate(clarification['options'], 1):
                    print(f"  {i}. {opt}")
            
            user_response = input("\nYour Answer: ").strip()
            if not user_response:
                print("Exiting due to empty response.")
                break
                
            # Update state with history and remove pending flag
            history = final_state.get("clarification_history", [])
            history.append({
                "question": clarification['question'],
                "answer": user_response
            })
            
            # Prepare next state: keep current state + updated history, remove pending
            current_state = {**final_state, "clarification_history": history}
            if "pending_clarification" in current_state:
                del current_state["pending_clarification"]
            
            print("\n🔄 Resuming workflow with new information...\n")
            continue
        
        # If no clarification needed, break
        break

    router_output = final_state.get("router_output")
    classifier_output = final_state.get("classifier_output")
    final_response = final_state.get("final_response")
    
    # Also support procedural guidance / activity law outputs
    procedural_state = final_state.get("procedural_guidance_state")
    activity_state = final_state.get("activity_law_state")

    print("\n" + "="*50)
    print("✅ FINAL OUTPUT")
    print("="*50)
    
    if final_response:
        print(final_response)
    elif procedural_state:
        print("\n[Procedural Guidance State Available]")
        if procedural_state.timeline_constraints:
            print(f"Timeline Constraints: {len(procedural_state.timeline_constraints.constraints)}")
        if procedural_state.checklist:
             print(f"Checklist Items: {len(procedural_state.checklist.items)}")
    elif activity_state:
         print("\n[Activity Law State Available]")
         if activity_state.fact_structuring:
             print(f"Factors: {len(activity_state.fact_structuring.factors)}")
             print(f"Events: {len(activity_state.fact_structuring.events)}")
    
    # print("\n=== Router Output ===")
    # print(router_output or "(no router output produced)")
    # print("\n=== Classifier Output ===")
    # print(classifier_output or "(no classifier output produced)")


if __name__ == "__main__":
    main()
