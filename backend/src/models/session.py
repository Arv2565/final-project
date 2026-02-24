from datetime import datetime
from typing import Optional, Dict, Any
from beanie import Document, Link
from pydantic import Field
from .user import User

class Session(Document):
    """
    Session model to store user authentication and active session state.
    """
    # Link to the User document (like Mongoose "ref")
    user: Link[User]
    token: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_info: Optional[Dict[str, Any]] = None
    
    is_active: bool = True
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "sessions"  # MongoDB collection name
        use_state_management = True
