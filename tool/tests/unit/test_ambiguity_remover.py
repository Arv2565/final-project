"""
Unit tests for AmbiguityRemover agent.

Tests cover:
1. Domain prompt registration and retrieval
2. Clarification necessity assessment
3. LLM response parsing
4. Clarification history tracking
5. Effectiveness marking and filtering
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.agents.ambiguity_remover import (
    AmbiguityRemover,
    ClarificationRequest,
    ClarificationResult,
)


@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing."""
    llm = AsyncMock()
    llm.ainvoke = AsyncMock()
    return llm


@pytest.fixture
def ambiguity_remover(mock_llm):
    """Create an AmbiguityRemover instance with mock LLM."""
    return AmbiguityRemover(
        llm=mock_llm,
        default_domains={
            "test_domain": "Test system prompt for {expertise_level}",
        },
        max_clarifications_per_agent=3,
        max_total_clarifications=5,
    )


class TestDomainPromptManagement:
    """Test domain prompt registration and retrieval."""
    
    def test_register_domain_prompt_static(self, ambiguity_remover):
        """Test registering a static domain prompt."""
        prompt = "This is a test prompt"
        ambiguity_remover.register_domain_prompt("custom", prompt)
        
        assert "custom" in ambiguity_remover.get_registered_domains()
        assert ambiguity_remover._get_system_prompt("custom") == prompt
    
    def test_register_domain_prompt_callable(self, ambiguity_remover):
        """Test registering a callable domain prompt."""
        def prompt_fn(expertise_level, context):
            return f"Prompt for {expertise_level}: {context.get('key', 'no key')}"
        
        ambiguity_remover.register_domain_prompt("callable_domain", prompt_fn)
        
        result = ambiguity_remover._get_system_prompt(
            "callable_domain",
            expertise_level="legal_professional",
            context={"key": "value"}
        )
        
        assert "legal_professional" in result
        assert "value" in result
    
    def test_get_registered_domains(self, ambiguity_remover):
        """Test retrieving list of registered domains."""
        domains = ambiguity_remover.get_registered_domains()
        
        assert isinstance(domains, list)
        assert "test_domain" in domains
    
    def test_unregistered_domain_raises_error(self, ambiguity_remover):
        """Test that accessing unregistered domain raises ValueError."""
        with pytest.raises(ValueError, match="Unknown scope"):
            ambiguity_remover._get_system_prompt("nonexistent")


class TestClarificationAssessment:
    """Test clarification necessity assessment."""
    
    @pytest.mark.asyncio
    async def test_assess_clarification_needed(self, ambiguity_remover, mock_llm):
        """Test when clarification is determined to be needed."""
        mock_response = MagicMock()
        mock_response.content = """NEEDS_CLARIFICATION: yes
CONFIDENCE: 0.6
QUESTION: Which state did this happen in?
REASON: To determine applicable laws
OPTIONS: None
IMPORTANCE: high
REASONING: Jurisdiction is critical for legal analysis"""
        
        mock_llm.ainvoke.return_value = mock_response
        
        result = await ambiguity_remover.assess_and_clarify(
            user_query="I have a problem",
            agent_context={"missing": ["jurisdiction"]},
            scope="test_domain",
            expertise_level="general_public",
        )
        
        assert result.needs_clarification is True
        assert result.clarification_request is not None
        assert result.clarification_request.question == "Which state did this happen in?"
        assert result.confidence == 0.6
    
    @pytest.mark.asyncio
    async def test_assess_clarification_not_needed(self, ambiguity_remover, mock_llm):
        """Test when clarification is determined to be unnecessary."""
        mock_response = MagicMock()
        mock_response.content = """NEEDS_CLARIFICATION: no
CONFIDENCE: 0.9
QUESTION: N/A
REASON: N/A
OPTIONS: None
IMPORTANCE: low
REASONING: Sufficient information available to proceed"""
        
        mock_llm.ainvoke.return_value = mock_response
        
        result = await ambiguity_remover.assess_and_clarify(
            user_query="Clear problem description",
            agent_context={"complete": True},
            scope="test_domain",
        )
        
        assert result.needs_clarification is False
        assert result.clarification_request is None
        assert result.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_max_clarifications_reached(self, ambiguity_remover, mock_llm):
        """Test behavior when max clarifications per agent is reached."""
        result = await ambiguity_remover.assess_and_clarify(
            user_query="Test query",
            agent_context={},
            scope="test_domain",
            clarification_count=3,  # Already at max
        )
        
        assert result.needs_clarification is False
        assert "Maximum clarification attempts" in result.reasoning
    
    @pytest.mark.asyncio
    async def test_expertise_level_passed_to_prompt(self, ambiguity_remover, mock_llm):
        """Test that expertise level is correctly passed to system prompt."""
        def expertise_aware_prompt(expertise_level, context):
            return f"Expertise: {expertise_level}"
        
        ambiguity_remover.register_domain_prompt("expertise_test", expertise_aware_prompt)
        
        mock_response = MagicMock()
        mock_response.content = "NEEDS_CLARIFICATION: no\nCONFIDENCE: 0.8\nREASONING: test"
        mock_llm.ainvoke.return_value = mock_response
        
        await ambiguity_remover.assess_and_clarify(
            user_query="Test",
            agent_context={},
            scope="expertise_test",
            expertise_level="legal_professional",
        )
        
        # Check that ainvoke was called
        assert mock_llm.ainvoke.called
        call_messages = mock_llm.ainvoke.call_args[0][0]
        
        # System message should contain expertise level
        assert any("legal_professional" in str(msg) for msg in call_messages)


class TestLLMResponseParsing:
    """Test parsing of LLM responses into ClarificationResult."""
    
    def test_parse_clarification_needed_response(self, ambiguity_remover):
        """Test parsing response when clarification is needed."""
        response = """NEEDS_CLARIFICATION: yes
CONFIDENCE: 0.7
QUESTION: Simple question here?
REASON: This is why we need it
OPTIONS: Option A, Option B, Option C
IMPORTANCE: medium
REASONING: Logical reasoning here"""
        
        result = ambiguity_remover._parse_llm_response(response, "test_domain")
        
        assert result.needs_clarification is True
        assert result.clarification_request.question == "Simple question here?"
        assert result.clarification_request.reason == "This is why we need it"
        assert result.clarification_request.importance == "medium"
        assert result.clarification_request.options == ["Option A", "Option B", "Option C"]
        assert result.confidence == 0.7
    
    def test_parse_no_clarification_needed_response(self, ambiguity_remover):
        """Test parsing response when clarification is not needed."""
        response = """NEEDS_CLARIFICATION: no
CONFIDENCE: 0.95
QUESTION: N/A
REASON: N/A
OPTIONS: None
IMPORTANCE: low
REASONING: Information already complete"""
        
        result = ambiguity_remover._parse_llm_response(response, "test_domain")
        
        assert result.needs_clarification is False
        assert result.clarification_request is None
        assert result.confidence == 0.95
    
    def test_parse_response_no_options(self, ambiguity_remover):
        """Test parsing response with no predefined options."""
        response = """NEEDS_CLARIFICATION: yes
CONFIDENCE: 0.5
QUESTION: What happened next?
REASON: Sequence of events matters
OPTIONS: None
IMPORTANCE: high
REASONING: Timeline is unclear"""
        
        result = ambiguity_remover._parse_llm_response(response, "test_domain")
        
        assert result.needs_clarification is True
        assert result.clarification_request.options is None


class TestClarificationTracking:
    """Test clarification history tracking and effectiveness marking."""
    
    def test_mark_clarification_used(self, ambiguity_remover):
        """Test marking a clarification as used."""
        history = [
            {
                "clarification_id": "id-1",
                "question": "Question 1",
                "answer": "Answer 1",
                "is_used": False,
            },
            {
                "clarification_id": "id-2",
                "question": "Question 2",
                "answer": "Answer 2",
                "is_used": False,
            },
        ]
        
        updated = ambiguity_remover.mark_clarification_used(
            "id-1",
            history,
            resolution_feedback="Resolved jurisdiction"
        )
        
        assert updated[0]["is_used"] is True
        assert updated[0]["resolution_feedback"] == "Resolved jurisdiction"
        assert updated[1]["is_used"] is False
    
    def test_get_useful_history(self, ambiguity_remover):
        """Test filtering history to only useful clarifications."""
        history = [
            {"clarification_id": "id-1", "question": "Q1", "is_used": True},
            {"clarification_id": "id-2", "question": "Q2", "is_used": False},
            {"clarification_id": "id-3", "question": "Q3", "is_used": True},
            {"clarification_id": "id-4", "question": "Q4", "is_used": False},
        ]
        
        useful = ambiguity_remover.get_useful_history(history)
        
        assert len(useful) == 2
        assert all(item["is_used"] for item in useful)
        assert useful[0]["clarification_id"] == "id-1"
        assert useful[1]["clarification_id"] == "id-3"
    
    def test_cleanup_unused_clarifications(self, ambiguity_remover):
        """Test cleanup stats for unused clarifications."""
        history = [
            {"clarification_id": "id-1", "question": "Q1", "is_used": True},
            {"clarification_id": "id-2", "question": "Q2", "is_used": False},
            {"clarification_id": "id-3", "question": "Q3", "is_used": False},
        ]
        
        stats = ambiguity_remover.cleanup_unused_clarifications(history)
        
        assert stats["original_count"] == 3
        assert stats["useful_count"] == 1
        assert stats["unused_removed"] == 2


class TestClarificationRequest:
    """Test ClarificationRequest model."""
    
    def test_clarification_request_creation(self):
        """Test creating a ClarificationRequest."""
        req = ClarificationRequest(
            question="Test question?",
            reason="Test reason",
            scope="test",
            importance="high",
            options=["A", "B"],
        )
        
        assert req.question == "Test question?"
        assert req.reason == "Test reason"
        assert req.scope == "test"
        assert req.importance == "high"
        assert req.options == ["A", "B"]
        assert req.clarification_id is not None
        assert req.is_used is False
    
    def test_clarification_request_dict(self):
        """Test converting ClarificationRequest to dict."""
        req = ClarificationRequest(
            question="Q?",
            reason="R",
            scope="test",
        )
        
        req_dict = req.dict()
        
        assert req_dict["question"] == "Q?"
        assert "clarification_id" in req_dict
        assert req_dict["is_used"] is False


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_unregistered_domain_error(self, ambiguity_remover, mock_llm):
        """Test error when scope is not registered."""
        with pytest.raises(ValueError):
            await ambiguity_remover.assess_and_clarify(
                user_query="Test",
                agent_context={},
                scope="nonexistent_domain",
            )
    
    @pytest.mark.asyncio
    async def test_llm_invocation_error(self, ambiguity_remover, mock_llm):
        """Test graceful handling of LLM errors."""
        mock_llm.ainvoke.side_effect = Exception("LLM error")
        
        result = await ambiguity_remover.assess_and_clarify(
            user_query="Test",
            agent_context={},
            scope="test_domain",
        )
        
        # Should return safe default
        assert result.needs_clarification is False
        assert "error" in result.reasoning.lower() or "unexpected" in result.reasoning.lower()
