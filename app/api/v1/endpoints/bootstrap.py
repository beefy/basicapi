from fastapi import APIRouter, HTTPException
from datetime import datetime
from ....core.deps import api_keys_db
from ....core.security import generate_api_key, hash_api_key
from ....models.schemas import APIKeyResponse

router = APIRouter()


@router.post("/bootstrap-admin", response_model=APIKeyResponse)
async def bootstrap_admin_key():
    """Create the first admin API key (only works if no admin keys exist)"""
    # Check if any admin keys already exist
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