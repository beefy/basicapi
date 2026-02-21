from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from ....db.mongodb import get_database
from ....models.schemas import (
    ResponseTimeCreate,
    ResponseTimeResponse,
    ResponseTimeStats,
    User
)
from ....core.deps import get_current_active_user

router = APIRouter()


@router.post("/", response_model=ResponseTimeResponse)
async def create_response_time(
    response_time: ResponseTimeCreate,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_database)
):
    """Store response time data (requires authentication)"""
    response_time_dict = response_time.model_dump()
    result = await db.responses.insert_one(response_time_dict)
    created_response_time = await db.responses.find_one({"_id": result.inserted_id})
    return ResponseTimeResponse(**created_response_time)


@router.get("/stats", response_model=List[ResponseTimeStats])
async def get_response_time_stats(
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    start_date: Optional[datetime] = Query(None, description="Start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering"),
    db=Depends(get_database)
):
    """Query response time statistics (returns average response times, not individual records)"""
    match_stage = {}
    
    if agent_name:
        match_stage["agent_name"] = agent_name
    
    if start_date or end_date:
        match_stage["received_ts"] = {}
        if start_date:
            match_stage["received_ts"]["$gte"] = start_date
        if end_date:
            match_stage["received_ts"]["$lte"] = end_date
    
    pipeline = [
        {"$match": match_stage},
        {
            "$addFields": {
                "response_time_ms": {
                    "$subtract": [
                        {"$toLong": "$sent_ts"},
                        {"$toLong": "$received_ts"}
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": "$agent_name",
                "average_response_time_ms": {"$avg": "$response_time_ms"},
                "count": {"$sum": 1}
            }
        },
        {
            "$project": {
                "agent_name": "$_id",
                "average_response_time_ms": 1,
                "count": 1,
                "_id": 0
            }
        },
        {"$sort": {"agent_name": 1}}
    ]
    
    cursor = db.responses.aggregate(pipeline)
    stats = []
    async for doc in cursor:
        stats.append(ResponseTimeStats(**doc))
    
    return stats
