from datetime import datetime
from typing import Optional, List, Any
from pydantic import EmailStr, Field
from beanie import Document, Indexed

class User(Document):
    """
    User model representing a registered user in the system.
    Inspired by Mongoose schemas, using Beanie (FastAPI's ODM).
    """
    name: str
    username: Indexed(str, unique=True)
    email: Indexed(EmailStr, unique=True)
    password: str
    phone: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    location: Optional[str] = None
    address: Optional[str] = None
    bio: Optional[str] = None
    
    # Unified profile picture field
    profile_picture_url: Optional[str] = None
    
    # Store list of allowed tags or interests
    tags: List[str] = Field(default_factory=list)
    
    # References (using strings or arbitrary dicts until Book/ExchangeRequest models are defined)
    previousPurchases: List[Any] = Field(default_factory=list)
    currentPosts: List[Any] = Field(default_factory=list)
    postHistory: List[Any] = Field(default_factory=list)
    requestsSent: List[Any] = Field(default_factory=list)
    requestsReceived: List[Any] = Field(default_factory=list)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"  # MongoDB collection name
        use_state_management = True
