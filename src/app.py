import argparse
from typing import Dict, Any

from src.workflows.chat import build_graph, GraphState


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a simple two-agent LangGraph pipeline (Research -> Writer)."
    )
    parser.add_argument(
        "--question",
        "-q",
        type=str,
        help="User question to pass into the graph. If omitted, you will be prompted.",
    )
    parser.add_argument(
        "--instructions",
        "-i",
        type=str,
        default="",
        help="Optional authoring instructions for the WriterAgent.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    question = args.question or input("Enter your question: ").strip()
    instructions = args.instructions.strip()

    if not question:
        raise SystemExit("A question is required to run the graph.")

    initial_state: GraphState = {
        "question": question,
    }
    if instructions:
        initial_state["instructions"] = instructions

    graph = build_graph()

    # Synchronous single-run invocation
    final_state: Dict[str, Any] = graph.invoke(initial_state)

    research_notes = final_state.get("research_notes", "").strip()
    answer = final_state.get("answer", "").strip()

    print("\n=== Research Notes ===")
    print(research_notes or "(no research notes produced)")
    print("\n=== Final Answer ===")
    print(answer or "(no answer produced)")


if __name__ == "__main__":
    main()
