from datetime import datetime
from typing import Optional, List, Dict, Any
from beanie import Document, Link
from pydantic import Field
from .user import User
from .session import Session

class Message(Document):
    """
    Message model representing a single chat interaction (e.g., from user or assistant).
    """
    sender: str  # e.g., "user", "agent", "system"
    content: str
    document: Optional[Dict[str, Any]] = None  # Stores generated document or structured content alongside the message
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "messages"

class ChatHistory(Document):
    """
    ChatHistory model representing a full conversation thread.
    """
    # Link to the User document
    user: Link[User]
    
    # Optional link to a specific session
    session: Optional[Link[Session]] = None
    
    title: Optional[str] = "New Chat"
    
    # List of Message documents (similar to Mongoose array of refs)
    messages: List[Link[Message]] = Field(default_factory=list)
    
    status: str = "active"  # e.g., "active", "archived"
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "chat_histories"  # MongoDB collection name
        use_state_management = True
