import os
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from beanie import PydanticObjectId

from ..models.user import User
from ..models.session import Session

ACCESS_KEY = os.getenv("ACCESS_KEY", "your_super_secret_access_key")
REFRESH_KEY = os.getenv("REFRESH_KEY", "your_super_secret_refresh_key")
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_access_token(user: User) -> str:
    data = {"id": str(user.id), "name": user.name, "username": user.username}
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=5)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, ACCESS_KEY, algorithm=ALGORITHM)

async def create_refresh_token_session(user: User, token: str) -> Session:
    expire = datetime.utcnow() + timedelta(hours=1)
    session = Session(
        user=user,
        token=token,
        expires_at=expire
    )
    await session.insert()
    return session

async def get_refresh_token(user: User) -> str:
    data = {"id": str(user.id), "name": user.name, "username": user.username}
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=1)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, REFRESH_KEY, algorithm=ALGORITHM)
    await create_refresh_token_session(user, token)
    return token

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, ACCESS_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("id")
        if user_id is None:
            raise credentials_exception
    except jwt.JWTError:
        raise credentials_exception
        
    user = await User.get(PydanticObjectId(user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    return user
