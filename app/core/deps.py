from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..core.security import verify_token
from ..models.schemas import User
from typing import Optional


security = HTTPBearer()


# For demo purposes, we'll use a simple in-memory user store
# In production, this should be in a proper database
fake_users_db = {
    "admin": {
        "username": "admin",
        "full_name": "Admin User",
        "email": "admin@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        "disabled": False,
    }
}


def get_user(username: str) -> Optional[User]:
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return User(**user_dict)
    return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    username = verify_token(token)
    
    if username is None:
        raise credentials_exception
        
    user = get_user(username=username)
    if user is None:
        raise credentials_exception
        
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
