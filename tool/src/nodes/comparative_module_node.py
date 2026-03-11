import logging
import importlib
from typing import Any, Dict, Optional

from langchain_core.runnables import RunnableConfig

def observe(name: str = "", as_type: str = ""):
    try:
        decorators_module = importlib.import_module("langfuse.decorators")
        return decorators_module.observe(name=name, as_type=as_type)
    except Exception:
        def decorator(func):
            return func
        return decorator

from src.models import GraphState
from src.agents.comparative_module_agent import ComparativeModuleAgent

logger = logging.getLogger(__name__)


@observe(name="ComparativeModule_Node", as_type="agent")
def comparative_module_node(state: GraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Run comparative module (Agent 6) with table-first routing."""
    try:
        agent = ComparativeModuleAgent()
        callbacks = config.get("callbacks", []) if config else []
        result = agent(state, callbacks=callbacks)

        logger.info(
            "Comparative module completed: mode=%s match_id=%s",
            result.get("comparison_mode"),
            result.get("comparison_match_id"),
        )

        if result.get("pending_clarification"):
            return result

        response_text = result.get("final_response", "")
        messages = state.get("messages", [])
        if response_text:
            messages = messages + [{"role": "assistant", "content": response_text}]

        return {
            **result,
            "messages": messages,
        }
    except Exception as exc:
        logger.error("Comparative module failed: %s", exc, exc_info=True)
        fallback = "Unable to generate comparison right now. Please retry with topic and states."
        return {
            "comparison_result": fallback,
            "final_response": fallback,
            "comparison_mode": "error",
        }
