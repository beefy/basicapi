from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from ....db.mongodb import get_database
from ....models.schemas import (
    StatusUpdateCreate,
    StatusUpdateResponse,
    QueryParams,
    User
)
from ....core.deps import get_current_active_user

router = APIRouter()


@router.post("/", response_model=StatusUpdateResponse)
async def create_status_update(
    status_update: StatusUpdateCreate,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_database)
):
    """Store a new status update (requires authentication)"""
    status_update_dict = status_update.model_dump()
    result = await db.status_updates.insert_one(status_update_dict)
    created_status_update = await db.status_updates.find_one({"_id": result.inserted_id})
    return StatusUpdateResponse(**created_status_update)


@router.get("/", response_model=List[StatusUpdateResponse])
async def get_status_updates(
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    start_date: Optional[datetime] = Query(None, description="Start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering"),
    limit: int = Query(100, le=1000, description="Number of records to return"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    db=Depends(get_database)
):
    """Query status updates"""
    filter_dict = {}
    
    if agent_name:
        filter_dict["agent_name"] = agent_name
    
    if start_date or end_date:
        filter_dict["timestamp"] = {}
        if start_date:
            filter_dict["timestamp"]["$gte"] = start_date
        if end_date:
            filter_dict["timestamp"]["$lte"] = end_date
    
    cursor = db.status_updates.find(filter_dict).skip(skip).limit(limit).sort("timestamp", -1)
    status_updates = []
    async for doc in cursor:
        status_updates.append(StatusUpdateResponse(**doc))
    
    return status_updates
