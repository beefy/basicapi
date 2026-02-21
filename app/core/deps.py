from fastapi import Depends, HTTPException, status, Request
from fastapi.security import APIKeyHeader
from ..core.security import hash_api_key
from ..models.schemas import User
from typing import Optional
import hashlib

api_key_header = APIKeyHeader(name="X-API-Key")
device_id_header = APIKeyHeader(name="X-Device-ID", auto_error=False)

# API keys storage with device fingerprinting
# Format: {"hashed_key": {"name": "pi-1", "device_id": "fingerprint", "is_admin": False, "created_at": datetime}}
api_keys_db = {}


def verify_device_fingerprint(device_id: str, stored_device_id: str) -> bool:
    """Verify device fingerprint matches stored fingerprint"""
    return device_id == stored_device_id


async def get_current_user(
    api_key: str = Depends(api_key_header),
    device_id: Optional[str] = Depends(device_id_header)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key or device fingerprint",
    )
    
    # Verify API key exists
    hashed_key = hash_api_key(api_key)
    if hashed_key not in api_keys_db:
        raise credentials_exception
    
    key_data = api_keys_db[hashed_key]
    
    # For admin keys, device ID is optional
    if key_data.get("is_admin", False):
        if device_id and not verify_device_fingerprint(device_id, key_data.get("device_id", "")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Device fingerprint mismatch for admin key"
            )
    else:
        # For regular keys, device ID is required and must match
        if not device_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Device ID required for this API key"
            )
        
        if not verify_device_fingerprint(device_id, key_data.get("device_id", "")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Device fingerprint mismatch"
            )
    
    # Update last used time
    from datetime import datetime
    api_keys_db[hashed_key]["last_used"] = datetime.utcnow()
    
    # Return user object
    return User(
        username=f"api-key:{key_data['name']}",
        full_name=f"API Key: {key_data['name']}",
        disabled=False
    )


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Require admin API key for certain operations"""
    # Check if this user comes from an admin API key
    username = current_user.username
    if not username.startswith("api-key:"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Find the API key and check if it's admin
    key_name = username.replace("api-key:", "")
    for hashed_key, key_data in api_keys_db.items():
        if key_data["name"] == key_name and key_data.get("is_admin", False):
            return current_user
    
    raise HTTPException(status_code=403, detail="Admin API key required")
