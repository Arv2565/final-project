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

    # Synchronous single-run invocation
    final_state: Dict[str, Any] = graph.invoke(initial_state)

    router_output = final_state.get("router_output")
    classifier_output = final_state.get("classifier_output")

    print("\n=== Router Output ===")
    print(router_output or "(no router output produced)")
    print("\n=== Classifier Output ===")
    print(classifier_output or "(no classifier output produced)")


if __name__ == "__main__":
    main()
