"""Chat endpoints for legal query processing."""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
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

from ..middleware.auth import authenticate

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: dict = Depends(authenticate)):
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
    Requires a valid JWT token passed as `token` query param.
    """
    import os
    from jose import jwt, JWTError

    token = websocket.query_params.get("token")
    if not token:
        await websocket.accept()
        await websocket.close(code=4001, reason="Missing authentication token")
        return

    access_key = os.getenv("ACCESS_KEY")
    try:
        verified_user = jwt.decode(token, access_key, algorithms=["HS256"])
    except JWTError as e:
        await websocket.accept()
        await websocket.close(code=4001, reason=f"Invalid token: {str(e)}")
        return

    try:
        await websocket.accept()
        logger.info(f"WebSocket connection established for user {verified_user.get('id')}")

        try:
            chat_service = get_chat_service()
            logger.info("ChatService initialized successfully")

            # Delegate entire handling logic to the service
            # Pass verified user from token (not from untrusted query params)
            await chat_service.handle_websocket(websocket, verified_user=verified_user)

        except WebSocketDisconnect:
            logger.info("WebSocket connection closed by client")
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}", exc_info=True)
            try:
                await websocket.send_json({"type": "error", "payload": f"Server error: {str(e)}"})
            except:
                logger.warning("Could not send error message to client")
            try:
                await websocket.close(code=1011, reason=str(e))
            except:
                logger.warning("Could not close WebSocket connection")
    except Exception as e:
        logger.error(f"WebSocket accept or initialization failed: {str(e)}", exc_info=True)

