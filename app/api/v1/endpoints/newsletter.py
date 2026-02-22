from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from datetime import datetime
from ....db.mongodb import get_database
from ....models.schemas import (
    NewsletterEmailCreate,
    NewsletterEmailResponse,
    User
)
from ....core.deps import get_current_user

router = APIRouter()


@router.post("/subscribe", response_model=dict)
async def subscribe_to_newsletter(
    newsletter_email: NewsletterEmailCreate,
    db=Depends(get_database)
):
    """Subscribe to email newsletter (public endpoint)"""
    try:
        # Add timestamp for when they subscribed
        email_data = newsletter_email.model_dump()
        email_data["subscribed_at"] = datetime.utcnow()
        
        result = await db.newsletter_emails.insert_one(email_data)
        
        return {
            "message": "Successfully subscribed to newsletter",
            "email": newsletter_email.email
        }
    except Exception as e:
        # Handle duplicate email error (unique constraint)
        if "duplicate key error" in str(e).lower() or "E11000" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already subscribed to newsletter"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to subscribe to newsletter"
        )


@router.get("/unsubscribe")
async def unsubscribe_from_newsletter(
    email: str = Query(..., description="Email address to unsubscribe"),
    db=Depends(get_database)
):
    """Unsubscribe from email newsletter (public endpoint, GET for easy email linking)"""
    try:
        result = await db.newsletter_emails.delete_one({"email": email})
        
        if result.deleted_count == 0:
            return {
                "message": "Email not found in newsletter list",
                "email": email
            }
        
        return {
            "message": "Successfully unsubscribed from newsletter",
            "email": email
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unsubscribe from newsletter"
        )


@router.get("/", response_model=List[NewsletterEmailResponse])
async def get_newsletter_emails(
    current_user: User = Depends(get_current_user),
    limit: int = Query(100, le=1000, description="Number of records to return"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    db=Depends(get_database)
):
    """Get all newsletter subscribers (requires authentication)"""
    try:
        cursor = db.newsletter_emails.find().skip(skip).limit(limit).sort("subscribed_at", -1)
        emails = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string for response
        for email_doc in emails:
            if "_id" in email_doc:
                email_doc["_id"] = str(email_doc["_id"])
        
        return [NewsletterEmailResponse(**email_doc) for email_doc in emails]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve newsletter emails"
        )