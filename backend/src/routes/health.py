"""Health check endpoint."""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Health check endpoint to verify the API is running.
    
    Returns:
        dict: Health status information
    """
    return {
        "status": "healthy",
        "service": "legal-assistant-api",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }
