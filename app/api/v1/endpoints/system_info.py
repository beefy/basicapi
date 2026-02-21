from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from ....db.mongodb import get_database
from ....models.schemas import (
    SystemInfoCreate,
    SystemInfoResponse,
    User
)
from ....core.deps import get_current_active_user

router = APIRouter()


@router.post("/", response_model=SystemInfoResponse)
async def create_system_info(
    system_info: SystemInfoCreate,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_database)
):
    """Store system information (requires authentication)"""
    system_info_dict = system_info.model_dump()
    result = await db.system_info.insert_one(system_info_dict)
    created_system_info = await db.system_info.find_one({"_id": result.inserted_id})
    return SystemInfoResponse(**created_system_info)


@router.get("/", response_model=List[SystemInfoResponse])
async def get_system_info(
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    start_date: Optional[datetime] = Query(None, description="Start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering"),
    limit: int = Query(100, le=1000, description="Number of records to return"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    db=Depends(get_database)
):
    """Query system information"""
    filter_dict = {}
    
    if agent_name:
        filter_dict["agent_name"] = agent_name
    
    if start_date or end_date:
        filter_dict["ts"] = {}
        if start_date:
            filter_dict["ts"]["$gte"] = start_date
        if end_date:
            filter_dict["ts"]["$lte"] = end_date
    
    cursor = db.system_info.find(filter_dict).skip(skip).limit(limit).sort("ts", -1)
    system_infos = []
    async for doc in cursor:
        system_infos.append(SystemInfoResponse(**doc))
    
    return system_infos
