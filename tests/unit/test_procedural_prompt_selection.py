import pytest
from unittest.mock import MagicMock, patch
from src.agents.procedural.response_generation import ProceduralResponseGenerationAgent, PROCEDURAL_RESPONSE_PROMPT
from src.prompts.procedural_civil_prompts import CIVIL_PROCEDURAL_RESPONSE_PROMPT
from src.models import GraphState, ProceduralGuidanceState, QueryRouterOutput
from src.models.query_router import QueryMetadata

@pytest.fixture
def mock_llm_helper():
    with patch("src.agents.procedural.response_generation.get_agent_llm") as mock_get:
        mock_llm = MagicMock()
        mock_get.return_value = mock_llm
        
        # Mock successful response
        mock_output = MagicMock()
        mock_output.summary = "Test Summary"
        mock_output.detailed_response = "Test Detailed Response"
        mock_llm.invoke.return_value = mock_output
        
        yield mock_llm

def test_response_generation_uses_civil_prompt(mock_llm_helper):
    """Test that civil prompt is used when active_legal_domain is 'civil'."""
    agent = ProceduralResponseGenerationAgent()
    
    # Setup state
    state = GraphState(
        user_query="Test query",
        router_output=QueryRouterOutput(
            cleaned_query="Test query", 
            metadata=QueryMetadata(language="en", has_personal_data=False, is_legal_question=True)
        ),
        procedural_guidance_state=ProceduralGuidanceState(),
        active_legal_domain="civil"
    )
    
    agent(state)
    
    # Verify invoke call args
    call_args = mock_llm_helper.invoke.call_args
    messages = call_args[0][0]
    system_message = messages[0]
    
    assert system_message["role"] == "system"
    assert system_message["content"] == CIVIL_PROCEDURAL_RESPONSE_PROMPT

def test_response_generation_uses_criminal_prompt_default(mock_llm_helper):
    """Test that criminal prompt is used when active_legal_domain is default/missing."""
    agent = ProceduralResponseGenerationAgent()
    
    # Setup state (missing active_legal_domain, defaults to criminal logic)
    state = GraphState(
        user_query="Test query",
        router_output=QueryRouterOutput(
            cleaned_query="Test query", 
            metadata=QueryMetadata(language="en", has_personal_data=False, is_legal_question=True)
        ),
        procedural_guidance_state=ProceduralGuidanceState()
    )
    
    agent(state)
    
    # Verify invoke call args
    call_args = mock_llm_helper.invoke.call_args
    messages = call_args[0][0]
    system_message = messages[0]
    
    assert system_message["role"] == "system"
    assert system_message["content"] == PROCEDURAL_RESPONSE_PROMPT
