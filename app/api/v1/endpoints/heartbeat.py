from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from ....db.mongodb import get_database
from ....models.schemas import (
    HeartbeatCreate,
    HeartbeatResponse,
    User
)
from ....core.deps import get_current_active_user

router = APIRouter()


@router.post(\"/\", response_model=HeartbeatResponse)
async def create_heartbeat(
    heartbeat: HeartbeatCreate,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_database)
):
    \"\"\"Store/update heartbeat (requires authentication)
    
    Only stores a single heartbeat per agent_name (upsert behavior)
    \"\"\"
    heartbeat_dict = heartbeat.model_dump()
    
    # Use upsert to ensure only one heartbeat per agent
    result = await db.heartbeat.replace_one(
        {\"agent_name\": heartbeat.agent_name},
        heartbeat_dict,
        upsert=True
    )
    
    # Find the updated/created document
    updated_heartbeat = await db.heartbeat.find_one({\"agent_name\": heartbeat.agent_name})
    return HeartbeatResponse(**updated_heartbeat)


@router.get(\"/\", response_model=List[HeartbeatResponse])
async def get_heartbeats(
    agent_name: Optional[str] = Query(None, description=\"Filter by agent name\"),
    db=Depends(get_database)
):
    \"\"\"Query heartbeats\"\"\"
    filter_dict = {}
    
    if agent_name:
        filter_dict[\"agent_name\"] = agent_name
    
    cursor = db.heartbeat.find(filter_dict).sort(\"last_heartbeat_ts\", -1)
    heartbeats = []
    async for doc in cursor:
        heartbeats.append(HeartbeatResponse(**doc))
    
    return heartbeats
