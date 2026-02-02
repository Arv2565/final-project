from typing import Dict, Any, Optional
from langchain_core.runnables import RunnableConfig
from src.models import GraphState

def placeholder_node(state: GraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Generic placeholder node for unimplemented agents."""
    print("⚠️  This agent is not yet implemented. Passing through.")
    return state
