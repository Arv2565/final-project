from langgraph.graph import END
import os


def test_route_from_general_chat_defaults_to_end():
    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    from src.workflows.chat.builder import route_from_general_chat
    state = {"loop_to_orchestrator": False}
    assert route_from_general_chat(state) == END


def test_route_from_general_chat_can_loop_to_orchestrator():
    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    from src.workflows.chat.builder import route_from_general_chat
    state = {"loop_to_orchestrator": True}
    assert route_from_general_chat(state) == "orchestrator"
