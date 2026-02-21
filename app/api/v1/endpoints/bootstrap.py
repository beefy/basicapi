from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
from ....core.deps import api_keys_db
from ....core.security import generate_api_key, hash_api_key
from ....core.config import settings
from ....models.schemas import APIKeyResponse

router = APIRouter()


@router.post("/bootstrap-admin", response_model=APIKeyResponse)
async def bootstrap_admin_key(request: Request, bootstrap_secret: str):
    """Create the first admin API key (only works if no admin keys exist and correct secret provided)"""
    
    # Security check 1: Only allow from localhost
    client_host = request.client.host
    if client_host not in ["127.0.0.1", "::1", "localhost"]:
        raise HTTPException(
            status_code=403,
            detail="Bootstrap only allowed from localhost for security"
        )
    
    # Security check 2: Require correct bootstrap secret
    if bootstrap_secret != settings.bootstrap_secret:
        raise HTTPException(
            status_code=401,
            detail="Invalid bootstrap secret"
        )
    
    # Security check 3: No admin keys should exist
    admin_keys_exist = any(
        key_data.get("is_admin", False) 
        for key_data in api_keys_db.values()
    )
    
    if admin_keys_exist:
        raise HTTPException(
            status_code=400,
            detail="Admin API key already exists. Use existing admin key to create more keys."
        )
    
    # Generate first admin API key
    api_key = generate_api_key()
    hashed_key = hash_api_key(api_key)
    
    # Store in database
    api_keys_db[hashed_key] = {
        "name": "bootstrap-admin",
        "description": "Bootstrap admin API key",
        "device_id": None,  # Admin keys don't need device fingerprints
        "is_admin": True,
        "created_at": datetime.utcnow(),
        "last_used": None,
        "created_by": "system"
    }
    
    return APIKeyResponse(
        name="bootstrap-admin",
        key=api_key,
        description="Bootstrap admin API key",
        device_id=None,
        is_admin=True,
        created_at=api_keys_db[hashed_key]["created_at"]
    )