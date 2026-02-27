from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Any
from beanie import PydanticObjectId
from datetime import datetime

from ..models.user import User
from ..models.chat import ChatHistory, Message
from ..middleware.auth import authenticate
from ..schemas.chat_history import (
    ChatHistoryCreate,
    ChatHistoryUpdate,
    ChatHistoryResponse,
    ChatHistoryListResponse,
    MessageSchema,
    ChatHistoryNameUpdate,
    ChatHistoryNameResponse
)

router = APIRouter()

@router.post("/", response_model=ChatHistoryResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    chat_in: ChatHistoryCreate,
    current_user: dict = Depends(authenticate)
) -> Any:
    """Create a new chat history thread for the current user."""
    try:
        user_id = PydanticObjectId(current_user.get("id"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID in token")

    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_chat = ChatHistory(
        user=user,
        title=chat_in.title,
    )
    await new_chat.insert()
    
    return {
        "id": str(new_chat.id),
        "title": new_chat.title,
        "status": new_chat.status,
        "created_at": new_chat.created_at,
        "updated_at": new_chat.updated_at,
        "messages": []
    }

@router.get("/", response_model=List[ChatHistoryListResponse])
async def list_user_chats(
    current_user: dict = Depends(authenticate)
) -> Any:
    """Get all chat histories for the current user, excluding empty chats."""
    try:
        user_id = PydanticObjectId(current_user.get("id"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID in token")

    # Fetch all chats with links resolved, then filter in Python.
    # Beanie's Link[User] field does not support direct equality filtering
    # in the find() query — we must fetch with fetch_links=True and compare IDs.
    all_chats = await ChatHistory.find(fetch_links=True).sort(-ChatHistory.updated_at).to_list()
    
    result = []
    for chat in all_chats:
        # Authorization: only return chats belonging to this user
        try:
            if str(chat.user.id) != str(user_id):
                continue
        except Exception:
            continue
        # Only include chats with at least one message (filter out empty chats)
        if len(chat.messages) > 0:
            result.append({
                "id": str(chat.id),
                "title": chat.title,
                "status": chat.status,
                "created_at": chat.created_at,
                "updated_at": chat.updated_at,
                "message_count": len(chat.messages)
            })
    return result

@router.get("/{chat_id}", response_model=ChatHistoryResponse)
async def get_chat(
    chat_id: str,
    current_user: dict = Depends(authenticate)
) -> Any:
    """Get a specific chat history by ID, including its messages."""
    try:
        chat = await ChatHistory.get(PydanticObjectId(chat_id), fetch_links=True)
    except:
        raise HTTPException(status_code=400, detail="Invalid chat ID format")
        
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
        
    if str(chat.user.id) != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized to access this chat")
        
    messages_formated = []
    for msg in chat.messages:
        messages_formated.append({
            "id": str(msg.id),
            "sender": msg.sender,
            "content": msg.content,
            "document": msg.document,
            "metadata": msg.metadata,
            "created_at": msg.created_at
        })

    return {
        "id": str(chat.id),
        "title": chat.title,
        "status": chat.status,
        "created_at": chat.created_at,
        "updated_at": chat.updated_at,
        "messages": messages_formated
    }

@router.put("/{chat_id}/name", response_model=ChatHistoryNameResponse)
async def update_chat_name(
    chat_id: str,
    name_in: ChatHistoryNameUpdate,
    current_user: dict = Depends(authenticate)
) -> Any:
    """Update the name/title of a chat history."""
    try:
        chat = await ChatHistory.get(PydanticObjectId(chat_id), fetch_links=True)
    except:
        raise HTTPException(status_code=400, detail="Invalid chat ID format")
        
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
        
    if str(chat.user.id) != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized to access this chat")
    
    # Update the title
    chat.title = name_in.name
    chat.updated_at = datetime.utcnow()
    await chat.save()
    
    return {
        "id": str(chat.id),
        "name": chat.title
    }

@router.put("/{chat_id}", response_model=ChatHistoryResponse)
async def update_chat(
    chat_id: str,
    chat_in: ChatHistoryUpdate,
    current_user: dict = Depends(authenticate)
) -> Any:
    """Update title or status of a chat."""
    chat = await ChatHistory.get(PydanticObjectId(chat_id), fetch_links=True)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
        
    if str(chat.user.id) != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized to access this chat")
        
    if chat_in.title is not None:
        chat.title = chat_in.title
    if chat_in.status is not None:
        chat.status = chat_in.status
        
    chat.updated_at = datetime.utcnow()
    await chat.save()
    
    messages_formated = []
    for msg in chat.messages:
        messages_formated.append({
            "id": str(msg.id),
            "sender": msg.sender,
            "content": msg.content,
            "document": msg.document,
            "metadata": msg.metadata,
            "created_at": msg.created_at
        })

    return {
        "id": str(chat.id),
        "title": chat.title,
        "status": chat.status,
        "created_at": chat.created_at,
        "updated_at": chat.updated_at,
        "messages": messages_formated
    }

@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: str,
    current_user: dict = Depends(authenticate)
) -> None:
    """Delete a chat history and its associated messages."""
    chat = await ChatHistory.get(PydanticObjectId(chat_id), fetch_links=True)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
        
    if str(chat.user.id) != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized to access this chat")
        
    # Delete all associated messages first
    for msg in chat.messages:
        await msg.delete()
        
    # Then delete the chat history
    await chat.delete()
    return None
