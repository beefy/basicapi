from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from ..core.security import verify_password, get_password_hash
from ..core.config import settings
from ..db.mongodb import get_database
from ..models.schemas import User, TokenData
from typing import Optional
from datetime import datetime

security = HTTPBearer(auto_error=False)


async def get_users_collection():
    """Get the users collection from MongoDB"""
    db = await get_database()
    return db.users


async def get_user(username: str) -> Optional[dict]:
    """Get user from database"""
    collection = await get_users_collection()
    return await collection.find_one({"username": username})


async def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate user with username and password"""
    from ..core.config import settings
    
    # Check if username is in allowed list
    allowed_usernames = settings.get_allowed_usernames()
    if username not in allowed_usernames:
        return None  # Fail silently for security
    
    user = await get_user(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
        
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
        
    user = await get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
        
    return User(
        username=user["username"],
        full_name=user.get("full_name", user["username"]),
        disabled=user.get("disabled", False)
    )


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user (not disabled)"""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def create_user(username: str, password: str, full_name: str = None) -> dict:
    """Create a new user"""
    from ..core.config import settings
    
    collection = await get_users_collection()
    
    # Validate password length (bcrypt limitation)
    if len(password.encode('utf-8')) > 72:
        raise HTTPException(
            status_code=400, 
            detail="Password too long. Maximum 72 bytes allowed."
        )
    
    # Check if username is in allowed list
    allowed_usernames = settings.get_allowed_usernames()
    if username not in allowed_usernames:
        raise HTTPException(
            status_code=403, 
            detail=f"Username '{username}' not allowed. Contact admin."
        )
    
    # Check if user already exists
    if await get_user(username):
        raise HTTPException(status_code=400, detail="Username already registered")
    
    user_data = {
        "username": username,
        "full_name": full_name or username,
        "hashed_password": get_password_hash(password),
        "disabled": False,
        "created_at": datetime.utcnow()
    }
    
    await collection.insert_one(user_data)
    return user_data