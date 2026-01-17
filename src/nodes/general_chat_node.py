from typing import Dict, Any
from langchain_core.runnables import RunnableConfig

from src.models import GraphState
from src.agents.general_chat_agent import GeneralChatAgent

# Lazy initialization
_general_chat_agent = None

def general_chat_node(state: GraphState, config: RunnableConfig | None = None) -> Dict[str, Any]:
    """LangGraph node that delegates to GeneralChatAgent."""
    global _general_chat_agent
    
    if _general_chat_agent is None:
        _general_chat_agent = GeneralChatAgent()
        
    callbacks = config.get("callbacks", []) if config else []
    return _general_chat_agent(state, callbacks=callbacks)
