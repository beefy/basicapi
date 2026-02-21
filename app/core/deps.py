from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from ..core.security import verify_token, verify_api_key, hash_api_key
from ..models.schemas import User
from typing import Optional, Union
import ipaddress

security = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

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

# API keys storage (in production, store in database)
# Format: {"hashed_key": {"name": "pi-1", "description": "Raspberry Pi 1", "created_at": datetime, "last_used": datetime}}
api_keys_db = {}

# Allowed IP addresses/networks for API key access
ALLOWED_IPS = [
    "127.0.0.1",  # Localhost
    "::1",        # IPv6 localhost
    # Add your Raspberry Pi IPs here, e.g.:
    # "192.168.1.100",
    # "192.168.1.0/24",  # Entire subnet
]


def get_user(username: str) -> Optional[User]:
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return User(**user_dict)
    return None


def is_ip_allowed(ip: str) -> bool:
    """Check if IP is in allowed list"""
    try:
        client_ip = ipaddress.ip_address(ip)
        for allowed in ALLOWED_IPS:
            if "/" in allowed:  # CIDR notation
                if client_ip in ipaddress.ip_network(allowed, strict=False):
                    return True
            else:  # Single IP
                if str(client_ip) == allowed:
                    return True
        return False
    except ValueError:
        return False


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    api_key: Optional[str] = Depends(api_key_header)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Try API key authentication first
    if api_key:
        # Check IP allowlist for API key access
        client_ip = request.client.host
        if not is_ip_allowed(client_ip):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied from IP: {client_ip}"
            )
        
        # Verify API key
        hashed_key = hash_api_key(api_key)
        if hashed_key in api_keys_db:
            # Update last used time
            from datetime import datetime
            api_keys_db[hashed_key]["last_used"] = datetime.utcnow()
            # Return a service user for API key authentication
            return User(
                username=f"api-key:{api_keys_db[hashed_key]['name']}",
                full_name=f"API Key: {api_keys_db[hashed_key]['name']}",
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
