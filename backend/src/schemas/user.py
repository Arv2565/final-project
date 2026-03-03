from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    name: str
    username: str
    email: EmailStr
    password: str
    phone: str
    location: Optional[str] = ""
    address: Optional[str] = ""
    bio: Optional[str] = ""

class UserLogin(BaseModel):
    username: str
    password: str

class TokenRefresh(BaseModel):
    token: str

class TokenResponse(BaseModel):
    accessToken: str
    refreshToken: str

class UserResponse(BaseModel):
    id: str  # Beanie uses PydanticObjectId, we'll cast to str
    name: str
    username: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime
