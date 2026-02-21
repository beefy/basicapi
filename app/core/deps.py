from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from ..core.security import verify_token, verify_api_key, hash_api_key
from ..models.schemas import User
from typing import Optional, Union
import hashlib

security = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
device_id_header = APIKeyHeader(name="X-Device-ID", auto_error=False)

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

# API keys storage with device fingerprinting
# Format: {"hashed_key": {"name": "pi-1", "device_id": "hashed_device_fingerprint", "created_at": datetime, "last_used": datetime}}
api_keys_db = {}


def get_user(username: str) -> Optional[User]:
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return User(**user_dict)
    return None


def verify_device_fingerprint(device_id: str, stored_device_id: str) -> bool:
    """Verify device fingerprint matches stored fingerprint"""
    return device_id == stored_device_id


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    api_key: Optional[str] = Depends(api_key_header),
    device_id: Optional[str] = Depends(device_id_header)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Try API key authentication first
    if api_key:
        if not device_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Device ID required for API key authentication"
            )
        
        # Verify API key
        hashed_key = hash_api_key(api_key)
        if hashed_key in api_keys_db:
            key_data = api_keys_db[hashed_key]
            
            # Verify device fingerprint
            if not verify_device_fingerprint(device_id, key_data.get("device_id")):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Device fingerprint mismatch - this API key is registered to a different device"
                )
            
            # Update last used time
            from datetime import datetime
            api_keys_db[hashed_key]["last_used"] = datetime.utcnow()
            
            # Return a service user for API key authentication
            return User(
                username=f"api-key:{key_data['name']}",
                full_name=f"API Key: {key_data['name']}",
                disabled=False
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
    
    # Fall back to JWT token authentication
    if not credentials:
        raise credentials_exception
        
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
