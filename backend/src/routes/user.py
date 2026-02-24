from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import Any, List
from beanie import PydanticObjectId
import shutil
import os
import uuid

from ..models.user import User
from ..middleware.auth import authenticate

router = APIRouter()

# Directory to save uploaded images locally if not using S3/Cloudinary
UPLOAD_DIR = "uploads/images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/", response_model=None)
async def get_current_user_info(current_user: dict = Depends(authenticate)) -> Any:
    user = await User.get(PydanticObjectId(current_user.get("id")))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(current_user.get("id")),
        "username": current_user.get("username"),
        "name": current_user.get("name"),
        "email": user.email,
        "profilePicture": user.profile_picture_url,
        "imageUrl": user.profile_picture_url,
        "bio": user.bio,
        "location": user.location
    }

@router.get("/profile", response_model=None)
async def get_profile(current_user: dict = Depends(authenticate)) -> Any:
    user = await User.get(PydanticObjectId(current_user.get("id")))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Here we simulate populating 'currentPosts postHistory previousPurchases'
    # In Beanie, if these were set up as Links, we would use fetch_links=True.
    return user.dict(exclude={"password"})

@router.put("/profile", response_model=None)
async def update_profile(
    update_data: dict, # Using dict to accept arbitrary partial updates like Express
    current_user: dict = Depends(authenticate)
) -> Any:
    user = await User.get(PydanticObjectId(current_user.get("id")))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    for key, value in update_data.items():
        if hasattr(user, key) and key not in ["id", "password", "username", "email"]:
            setattr(user, key, value)
            
    await user.save()
    return user.dict(exclude={"password"})

@router.post("/image", response_model=None, status_code=status.HTTP_201_CREATED)
@router.post("/upload-image", response_model=None, status_code=status.HTTP_201_CREATED)
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(authenticate)
) -> Any:
    user = await User.get(PydanticObjectId(current_user.get("id")))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Simple local file save implementation matching the behavior
    file_extension = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Assume the URL to access it locally is /uploads/images/filename
    # Update the user profile
    image_url = f"/uploads/images/{filename}"
    user.profile_picture_url = image_url
    await user.save()
    
    return {
        "message": "Image uploaded successfully",
        "imageUrl": image_url,
        "profilePic": image_url,
        "user": user.dict(exclude={"password"})
    }

@router.get("/{id}", response_model=None)
async def get_user_by_id(id: str) -> Any:
    user = await User.get(PydanticObjectId(id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.dict(exclude={"password"})

@router.put("/{id}", response_model=None)
async def update_user_by_id(id: str, update_data: dict) -> Any:
    user = await User.get(PydanticObjectId(id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    for key, value in update_data.items():
        if hasattr(user, key) and key not in ["id", "password"]:
            setattr(user, key, value)
            
    await user.save()
    return user.dict(exclude={"password"})

@router.get("/{id}/posts/current", response_model=List[Any])
async def get_user_current_posts(id: str) -> Any:
    user = await User.get(PydanticObjectId(id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return getattr(user, "currentPosts", [])

@router.get("/{id}/posts/history", response_model=List[Any])
async def get_user_post_history(id: str) -> Any:
    user = await User.get(PydanticObjectId(id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return getattr(user, "postHistory", [])

@router.get("/{id}/purchases", response_model=List[Any])
async def get_user_purchases(id: str) -> Any:
    user = await User.get(PydanticObjectId(id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return getattr(user, "previousPurchases", [])
