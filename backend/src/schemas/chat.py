"""Pydantic models for chat request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="User's legal query"
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for conversation tracking"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What are the procedural steps for filing a divorce petition in India?",
                "session_id": "session_123"
            }
        }

class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    
    query: str = Field(..., description="The original user query")
    response: str = Field(..., description="AI-generated response")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the response"
    )
    session_id: Optional[str] = Field(
        None,
        description="Session ID for conversation tracking"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What are the procedural steps for filing a divorce petition?",
                "response": "Based on the procedural guidance...",
                "metadata": {
                    "intent": "procedural_guidance",
                    "confidence": 0.95,
                    "domain": "civil"
                },
                "session_id": "session_123"
            }
        }
