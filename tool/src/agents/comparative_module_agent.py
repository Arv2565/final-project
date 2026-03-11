from typing import Any, Dict, List

from src.agents.comparative_module.workflow import ComparativeModuleWorkflow
from src.models import GraphState


class ComparativeModuleAgent:
    """Thin wrapper that delegates comparative execution to the comparative workflow."""

    def __init__(self) -> None:
        self.workflow = ComparativeModuleWorkflow()

    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        query = state.get("input_query") or state.get("user_query") or ""
        return self.run(query, callbacks=callbacks)

    def run(self, query: str, callbacks: List[Any] = []) -> Dict[str, Any]:
        return self.workflow.run(query, callbacks=callbacks)
