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
from ....core.deps import get_current_user

router = APIRouter()


@router.post("/", response_model=StatusUpdateResponse)
async def create_status_update(
    status_update: StatusUpdateCreate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_database)
):
    """Store a new status update (requires authentication)"""
    status_update_dict = status_update.model_dump()
    
    # Debug: Print what we're about to insert
    print(f"DEBUG: Inserting status update: {status_update_dict}")
    print(f"DEBUG: Current user: {current_user}")
    print(f"DEBUG: Database: {db.name}")
    
    result = await db.status_updates.insert_one(status_update_dict)
    print(f"DEBUG: Insert result: {result.inserted_id}")
    
    created_status_update = await db.status_updates.find_one({"_id": result.inserted_id})
    print(f"DEBUG: Retrieved document: {created_status_update}")
    
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
    
    print(f"DEBUG GET: Filter dict: {filter_dict}")
    print(f"DEBUG GET: Database: {db.name}")
    print(f"DEBUG GET: Limit: {limit}, Skip: {skip}")
    
    # Check total count in collection
    total_count = await db.status_updates.count_documents({})
    print(f"DEBUG GET: Total documents in collection: {total_count}")
    
    cursor = db.status_updates.find(filter_dict).skip(skip).limit(limit).sort("timestamp", -1)
    status_updates = []
    async for doc in cursor:
        print(f"DEBUG GET: Found document: {doc}")
        status_updates.append(StatusUpdateResponse(**doc))
    
    print(f"DEBUG GET: Returning {len(status_updates)} status updates")
    return status_updates
