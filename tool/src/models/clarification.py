from pydantic import BaseModel, Field
from typing import List, Optional

class ClarificationRequest(BaseModel):
    """Request for clarification from the user."""
    question: str = Field(..., description="The specific question to ask the user.")
    reason: str = Field(..., description="Why this clarification is needed.")
    options: Optional[List[str]] = Field(None, description="Suggested options for the user to choose from.")
    criticality: str = Field("medium", description="Importance of this clarification: low, medium, high")
