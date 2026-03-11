from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class MessageSchema(BaseModel):
    id: str
    sender: str
    content: str
    document: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
class ChatHistoryCreate(BaseModel):
    title: Optional[str] = "New Chat"
    
class ChatHistoryUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None

class ChatHistoryResponse(BaseModel):
    id: str
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageSchema] = Field(default_factory=list)

class ChatHistoryListResponse(BaseModel):
    id: str
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    message_count: int

class ChatHistoryNameUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500, description="New name for the chat history")

class ChatHistoryNameResponse(BaseModel):
    id: str
    name: str


class ChatDocumentUpdate(BaseModel):
    content: str = Field(..., description="Updated document content from draft editor")


class ChatDocumentUpdateResponse(BaseModel):
    chat_id: str
    message_id: str
    updated_at: datetime
