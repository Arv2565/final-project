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

<<<<<<< HEAD
    # Initialize observability callback
    from src.config.observability import get_langfuse_callback
    callback_handler = get_langfuse_callback()
    config = {"callbacks": [callback_handler]} if callback_handler else {}

    # Synchronous single-run invocation with config
    final_state: Dict[str, Any] = graph.invoke(initial_state, config=config)

    router_output = final_state.get("router_output")
    classifier_output = final_state.get("classifier_output")

    print("\n=== Router Output ===")
    print(router_output or "(no router output produced)")
    print("\n=== Classifier Output ===")
    print(classifier_output or "(no classifier output produced)")

    # Generate PDF Report
    if final_state.get("final_response"):
        from src.utils.pdf_generator import generate_pdf_report
        import time
        
        timestamp = int(time.time())
        filename = f"output/response_{timestamp}.pdf"
        try:
            pdf_path = generate_pdf_report(final_state["final_response"], filename)
            print(f"\n📄 PDF Report generated: {pdf_path}")
        except Exception as e:
            print(f"\n❌ Failed to generate PDF: {e}")
=======
    # Initialize observability callback with session tracking
    from src.config.observability import get_langfuse_callback
    from langfuse import get_client
    import uuid
    
    session_id = str(uuid.uuid4())
    langfuse_client = None
    try:
        langfuse_client = get_client()
    except Exception:
        pass  # Langfuse not configured
    
    # Synchronous invocation loop
    current_state = initial_state
    clarification_count = 0
    MAX_CLARIFICATIONS = 5  # Prevent infinite loops
    iteration = 0
    
    while True:
        iteration += 1
        # Create callback handler with session and iteration metadata
        callback_handler = get_langfuse_callback()
        config = {"callbacks": [callback_handler]} if callback_handler else {}
        
        # Add session metadata to callback if available
        if callback_handler:
            callback_handler.session_id = session_id
            callback_handler.metadata = {
                "iteration": iteration,
                "clarification_count": clarification_count,
                "has_clarification_history": bool(current_state.get("clarification_history")),
            }
        
        print(f"\n{'='*80}")
        print(f"🔄 Iteration {iteration} (Session: {session_id[:8]}...)")
        print(f"{'='*80}")
        
        final_state: Dict[str, Any] = graph.invoke(current_state, config=config)
        
        # Check for clarification request
        if final_state.get("pending_clarification"):
            clarification_count += 1
            
            # Safety check for infinite loops
            if clarification_count > MAX_CLARIFICATIONS:
                print("\n⚠️  Maximum clarification limit reached. Proceeding with available information.")
                # Remove pending clarification and continue
                current_state = {**final_state}
                if "pending_clarification" in current_state:
                    del current_state["pending_clarification"]
                # Also clear orchestrator_plan to force re-execution
                if "orchestrator_plan" in current_state:
                    del current_state["orchestrator_plan"]
                continue
            
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
            
            # Map numeric response to actual option text if options are provided
            actual_answer = user_response
            if clarification.get('options') and user_response.isdigit():
                option_idx = int(user_response) - 1
                if 0 <= option_idx < len(clarification['options']):
                    actual_answer = clarification['options'][option_idx]
                
            # Update state with history and remove pending flag
            history = final_state.get("clarification_history", [])
            history.append({
                "question": clarification['question'],
                "answer": actual_answer
            })
            
            # Prepare next state: keep essential state but clear orchestrator_plan to force re-execution
            current_state = {
                "user_query": final_state.get("user_query"),
                "router_output": final_state.get("router_output"),
                "clarification_history": history,
                "clarification_counts": final_state.get("clarification_counts", {}),
            }
            # Keep any other non-orchestrator state that might be needed
            for key in final_state:
                if key not in ["pending_clarification", "orchestrator_plan", "user_query", "router_output", "clarification_history", "clarification_counts"]:
                    if key not in current_state:
                        current_state[key] = final_state[key]
            
            print("\n🔄 Resuming workflow with new information...\n")
            
            # Flush callback to ensure trace is sent before next iteration
            if langfuse_client:
                try:
                    langfuse_client.flush()
                except Exception as e:
                    print(f"Warning: Failed to flush LangFuse: {e}")
            
            continue
        
        # If no clarification needed, break
        break
    
    # Final flush to ensure all traces are sent
    if langfuse_client:
        try:
            langfuse_client.flush()
        except Exception as e:
            print(f"Warning: Failed to flush LangFuse: {e}")

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
>>>>>>> 14a165ddc199668c3ad8563ab4d99d899b1c0e5e


if __name__ == "__main__":
    main()
