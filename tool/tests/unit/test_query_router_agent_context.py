from unittest.mock import MagicMock, patch

from src.agents.query_router_agent import QueryRouterAgent
from src.models import GraphState, QueryRouterOutput
from src.models.query_router import QueryMetadata


def test_query_router_uses_chat_context():
    """Test that QueryRouterAgent uses chat_context field for conversational continuity."""
    with patch("src.agents.query_router_agent.get_agent_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        mock_llm.invoke.return_value = QueryRouterOutput(
            cleaned_query="Polished query",
            metadata=QueryMetadata(
                original_language="en",
                language="en",
                has_personal_data=False,
                is_legal_question=True,
            ),
        )

        agent = QueryRouterAgent()
        state = GraphState(
            user_query="What are my options now?",
            chat_context="Previous exchange:\nUser: I was terminated without notice.\nAssistant: Which state are you in?",
        )

        result = agent(state)

        assert "router_output" in result
        assert result["router_output"].cleaned_query == "Polished query"

        call_args = mock_llm.invoke.call_args
        messages = call_args[0][0]
        user_prompt = messages[1]["content"]

        assert "Previous exchange:" in user_prompt
        assert "I was terminated without notice." in user_prompt
