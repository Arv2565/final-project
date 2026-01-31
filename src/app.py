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


if __name__ == "__main__":
    main()
