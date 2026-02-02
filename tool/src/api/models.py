from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class ChatRequest(BaseModel):
    type: str # "query" or "clarification_response"
    payload: Any

class ChatResponse(BaseModel):
    type: str # "status", "clarification_request", "final_result", "error"
    payload: Any
