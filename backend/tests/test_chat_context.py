"""
Tests for chat_context functionality in chat service.

Ensures that chat_context is properly:
1. Extracted from chat history
2. Included in message metadata
3. Formatted correctly
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime


@pytest.mark.asyncio
async def test_extract_last_turn_context_formats_correctly():
    """Test that _extract_last_turn_context produces the expected formatted string."""
    from src.services.chat_service import _extract_last_turn_context
    from src.models.chat import Message
    
    # Mock chat history with messages
    user_msg = MagicMock()
    user_msg.sender = "user"
    user_msg.content = "I was terminated without notice."
    
    assistant_msg = MagicMock()
    assistant_msg.sender = "assistant"
    assistant_msg.content = "Which state are you in?"
    
    chat_history = MagicMock()
    chat_history.messages = [user_msg, assistant_msg]
    
    result = await _extract_last_turn_context(chat_history)
    
    assert "Previous exchange:" in result
    assert "User: I was terminated without notice." in result
    assert "Assistant: Which state are you in?" in result


@pytest.mark.asyncio
async def test_extract_last_turn_context_empty_history():
    """Test that _extract_last_turn_context returns empty string for empty history."""
    from src.services.chat_service import _extract_last_turn_context
    
    chat_history = MagicMock()
    chat_history.messages = []
    
    result = await _extract_last_turn_context(chat_history)
    
    assert result == ""


@pytest.mark.asyncio
async def test_extract_last_turn_context_only_user_message():
    """Test that _extract_last_turn_context handles user-only message gracefully."""
    from src.services.chat_service import _extract_last_turn_context
    
    user_msg = MagicMock()
    user_msg.sender = "user"
    user_msg.content = "Hello"
    
    chat_history = MagicMock()
    chat_history.messages = [user_msg]
    
    result = await _extract_last_turn_context(chat_history)
    
    assert "Previous user message: Hello" in result


@pytest.mark.asyncio
async def test_extract_last_turn_context_only_assistant_message():
    """Test that _extract_last_turn_context handles assistant-only message gracefully."""
    from src.services.chat_service import _extract_last_turn_context
    
    assistant_msg = MagicMock()
    assistant_msg.sender = "assistant"
    assistant_msg.content = "How can I help you?"
    
    chat_history = MagicMock()
    chat_history.messages = [assistant_msg]
    
    result = await _extract_last_turn_context(chat_history)
    
    assert "Previous assistant message: How can I help you?" in result


def test_message_metadata_schema_supports_chat_context():
    """Verify that Message schema metadata field can store chat_context."""
    # This is a structural test - we just ensure the field exists
    # and can be set without errors
    from src.schemas.chat_history import MessageSchema
    
    # Create a message schema with chat_context in metadata
    message_data = {
        "sender": "user",
        "content": "Test message",
        "created_at": datetime.utcnow(),
        "metadata": {
            "chat_context": "Previous exchange:\nUser: Hello\nAssistant: Hi there"
        }
    }
    
    # Pydantic should accept this structure
    schema = MessageSchema(**message_data)
    assert "chat_context" in schema.metadata
    assert schema.metadata["chat_context"] == "Previous exchange:\nUser: Hello\nAssistant: Hi there"
