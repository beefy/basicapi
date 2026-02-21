from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime
from ....core.deps import get_current_active_user, api_keys_db
from ....core.security import generate_api_key, hash_api_key
from ....models.schemas import User, APIKeyCreate, APIKeyResponse, APIKeyInfo

router = APIRouter()


@router.post("/create", response_model=APIKeyResponse)
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Create a new API key tied to a specific device (requires admin authentication)"""
    # Generate new API key
    api_key = generate_api_key()
    hashed_key = hash_api_key(api_key)
    
    # Store in database (in production, use proper database)
    api_keys_db[hashed_key] = {
        "name": api_key_data.name,
        "description": api_key_data.description,
        "device_id": api_key_data.device_id,
        "created_at": datetime.utcnow(),
        "last_used": None,
        "created_by": current_user.username
    }
    
    return APIKeyResponse(
        name=api_key_data.name,
        key=api_key,
        description=api_key_data.description,
        device_id=api_key_data.device_id,
        created_at=api_keys_db[hashed_key]["created_at"]
    )


@router.get("/list", response_model=List[APIKeyInfo])
async def list_api_keys(current_user: User = Depends(get_current_active_user)):
    """List all API keys (without showing the actual keys)"""
    keys = []
    for hashed_key, key_data in api_keys_db.items():
        # Show only partial device ID for security
        device_fingerprint = key_data["device_id"][:8] + "..." + key_data["device_id"][-8:] if len(key_data["device_id"]) > 16 else key_data["device_id"]
        
        keys.append(APIKeyInfo(
            name=key_data["name"],
            description=key_data["description"],
            device_fingerprint=device_fingerprint,
            created_at=key_data["created_at"],
            last_used=key_data["last_used"]
        ))
    return keys


@router.delete("/{key_name}")
async def delete_api_key(
    key_name: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete an API key by name"""
    # Find and remove the key
    to_delete = None
    for hashed_key, key_data in api_keys_db.items():
        if key_data["name"] == key_name:
            to_delete = hashed_key
            break
    
    if to_delete:
        del api_keys_db[to_delete]
        return {"message": f"API key '{key_name}' deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail=f"API key '{key_name}' not found")