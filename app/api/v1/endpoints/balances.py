from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from ....db.mongodb import get_database
from ....models.schemas import (
    BalanceCreate,
    BalanceResponse,
    BalanceUpload,
    BalanceUploadResponse,
    QueryParams,
    User
)
from ....core.deps import get_current_user

router = APIRouter()


@router.post("/upload", response_model=BalanceUploadResponse)
async def upload_balances(
    balance_upload: BalanceUpload,
    current_user: User = Depends(get_current_user),
    db=Depends(get_database)
):
    """Upload multiple balance records for an agent (requires authentication)"""
    
    if not balance_upload.balances:
        raise HTTPException(status_code=400, detail="No balances provided")
    
    # Prepare balance documents for insertion
    balance_docs = []
    for balance_item in balance_upload.balances:
        balance_doc = {
            "agent_name": balance_upload.agent_name,
            "token_name": balance_item.token_name,
            "token_amount_in_wallet": balance_item.token_amount_in_wallet,
            "token_value_usd": balance_item.token_value_usd,
            "timestamp": balance_upload.timestamp
        }
        balance_docs.append(balance_doc)
    
    # Insert all balance records
    result = await db.balances.insert_many(balance_docs)
    
    return BalanceUploadResponse(
        message=f"Successfully uploaded {len(result.inserted_ids)} balance records",
        agent_name=balance_upload.agent_name,
        records_inserted=len(result.inserted_ids),
        timestamp=datetime.utcnow()
    )
