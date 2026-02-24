from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any
from pydantic import BaseModel
from jose import jwt
import os

from ..models.user import User
from ..models.session import Session
from ..schemas.user import UserCreate, UserLogin, TokenResponse, TokenRefresh
from ..core.security import (
    get_password_hash, 
    verify_password, 
    get_access_token, 
    get_refresh_token,
    REFRESH_KEY,
    ALGORITHM
)

router = APIRouter()

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_in: UserCreate) -> Any:
    # Check if user exists
    user = await User.find_one(User.username == user_in.username)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    user_email = await User.find_one(User.email == user_in.email)
    if user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

    # Create new user
    new_user = User(
        username=user_in.username,
        password=get_password_hash(user_in.password),
        name=user_in.name,
        email=user_in.email,
        phone=user_in.phone,
        location=user_in.location,
        address=user_in.address,
        bio=user_in.bio,
        tags=user_in.tags or []
    )
    
    await new_user.insert()
    
    # Generate tokens
    access_token = get_access_token(new_user)
    refresh_token = await get_refresh_token(new_user)
    
    return {
        "accessToken": access_token,
        "refreshToken": refresh_token
    }

@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def login(user_in: UserLogin) -> Any:
    user = await User.find_one(User.username == user_in.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")
        
    if not verify_password(user_in.password, user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wrong password")
        
    access_token = get_access_token(user)
    refresh_token = await get_refresh_token(user)
    
    return {
        "accessToken": access_token,
        "refreshToken": refresh_token
    }

@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def refresh_token(token_in: TokenRefresh) -> Any:
    if not token_in.token:
        raise HTTPException(status_code=403, detail="Token not found")
        
    # Delete the old refresh token session
    session = await Session.find_one(Session.token == token_in.token)
    if not session:
        raise HTTPException(status_code=403, detail="Authorization failed")
    await session.delete()

    # Verify existing refresh token
    try:
        payload = jwt.decode(token_in.token, REFRESH_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("id")
        if not user_id:
            raise HTTPException(status_code=403, detail="Invalid token payload")
    except jwt.JWTError as e:
        raise HTTPException(status_code=403, detail=str(e))
        
    from beanie import PydanticObjectId
    user = await User.get(PydanticObjectId(user_id))
    if not user:
        raise HTTPException(status_code=403, detail="User not found")
        
    access_token = get_access_token(user)
    refresh_token_new = await get_refresh_token(user)
    
    return {
        "accessToken": access_token,
        "refreshToken": refresh_token_new
    }

@router.post("/logout", status_code=status.HTTP_201_CREATED)
async def logout(token_in: TokenRefresh) -> Any:
    session = await Session.find_one(Session.token == token_in.token)
    if session:
        await session.delete()
    return {"message": "Logged out succesfully"}
