import os
from fastapi import Request, HTTPException, status
from jose import jwt, JWTError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def authenticate(request: Request):
    """
    FastAPI dependency that acts like the Express authenticate middleware.
    It verifies the JWT token and attaches the decoded user payload to request.state.user.
    
    Usage:
    from fastapi import Depends
    from backend.src.middleware.auth import authenticate
    
    @router.get("/protected", dependencies=[Depends(authenticate)])
    async def protected_route(request: Request):
        user = request.state.user
        return {"message": "success", "user": user}
    """
    auth_header = request.headers.get('authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        # Raising 400 to match the provided Express JS logic
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Token not found"
        )
        
    token = auth_header.split(' ')[1]
    access_key = os.getenv("ACCESS_KEY")
    
    # Check if access_key is available
    if not access_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="ACCESS_KEY not configured in environment"
        )
    
    try:
        user = jwt.decode(token, access_key, algorithms=["HS256"])
        request.state.user = user
        return user
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
