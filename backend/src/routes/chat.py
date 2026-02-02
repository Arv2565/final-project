"""Chat endpoints for legal query processing."""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import logging

from ..services.chat_service import ChatService
from ..schemas.chat import ChatRequest, ChatResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Lazy initialization - create service instance when needed
_chat_service = None

def get_chat_service() -> ChatService:
    """Get or create the chat service instance."""
    global _chat_service
    if _chat_service is None:
        logger.info("Initializing ChatService...")
        _chat_service = ChatService()
    return _chat_service

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a legal query using the AI tool.
    
    Args:
        request: ChatRequest containing the user query
        
    Returns:
        ChatResponse with the AI-generated response
        
    Raises:
        HTTPException: If processing fails
    """
    try:
        chat_service = get_chat_service()
        logger.info(f"Processing query: {request.query[:100]}...")
        result = await chat_service.process_query(
            query=request.query,
            session_id=request.session_id
        )
        return ChatResponse(**result)
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )

@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat with streaming responses.
    
    Args:
        websocket: WebSocket connection
    """
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        chat_service = get_chat_service()
        
        # Delegate entire handling logic to the service
        # The service method now implements the full loop, streaming, and clarification logic
        await chat_service.handle_websocket(websocket)
            
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}", exc_info=True)
        # Try to close if still open
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass
