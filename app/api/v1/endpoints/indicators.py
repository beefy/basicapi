"""Technical indicators endpoint"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging
import asyncio

from ....models.schemas import IndicatorsResponse, TokenIndicators
from ....core.deps import get_current_active_user
from ....core.cache import IndicatorCache
from ....core.indicators import get_all_token_indicators

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@router.get("/indicators", response_model=IndicatorsResponse, dependencies=[Depends(get_current_active_user)])
async def get_technical_indicators():
    """
    Get cached technical indicators for all supported tokens (requires authentication).
    
    Returns cached indicator data from the database. Data is refreshed on-demand
    by calling the refresh endpoint before querying indicators.
    """
    try:
        logger.info("Fetching cached technical indicators")
        
        # Get all cached indicators
        cached_indicators = await IndicatorCache.get_all_cached_indicators()
        
        if not cached_indicators:
            # No cached data found
            raise HTTPException(
                status_code=404,
                detail="No cached indicator data available. Call the refresh endpoint first to generate indicators."
            )
        
        # Convert to response format
        indicators = {}
        summary_info = None
        oldest_timestamp = None
        newest_timestamp = None
        
        for token_symbol, indicator_data in cached_indicators.items():
            if token_symbol == "_summary":
                summary_info = indicator_data
                continue
            
            if indicator_data is None:
                indicators[token_symbol] = None
                continue
                
            # Parse timestamp to calculate cache age
            try:
                indicator_timestamp = datetime.fromisoformat(indicator_data['timestamp'].replace('Z', '+00:00'))
                if oldest_timestamp is None or indicator_timestamp < oldest_timestamp:
                    oldest_timestamp = indicator_timestamp
                if newest_timestamp is None or indicator_timestamp > newest_timestamp:
                    newest_timestamp = indicator_timestamp
            except Exception as e:
                logger.warning(f"Error parsing timestamp for {token_symbol}: {e}")
            
            # Convert to TokenIndicators model
            try:
                indicators[token_symbol] = TokenIndicators(**indicator_data)
            except Exception as e:
                logger.error(f"Error converting indicators for {token_symbol}: {e}")
                indicators[token_symbol] = None
        
        # Calculate cache age
        cache_age_minutes = None
        if oldest_timestamp:
            cache_age_minutes = int((datetime.utcnow() - oldest_timestamp.replace(tzinfo=None)).total_seconds() / 60)
        
        # Use cached timestamp if available
        cached_at = oldest_timestamp.isoformat() if oldest_timestamp else None
        
        logger.info(f"Retrieved {len([v for v in indicators.values() if v is not None])} cached indicators")
        
        return IndicatorsResponse(
            indicators=indicators,
            summary=summary_info or {"message": "Summary information not available"},
            cached_at=cached_at,
            cache_age_minutes=cache_age_minutes
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error retrieving cached indicators: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error retrieving indicators: {str(e)}"
        )


@router.post("/indicators/refresh", dependencies=[Depends(get_current_active_user)])
async def refresh_technical_indicators():
    """
    Refresh technical indicators for all tokens (requires authentication).
    
    This endpoint triggers the indicator calculation and caching process.
    Call this endpoint to generate fresh indicator data before querying indicators.
    """
    try:
        logger.info("Starting manual refresh of technical indicators")
        
        # Run the indicator calculation
        results = await get_all_token_indicators()
        
        # Cache each token's indicators individually
        cached_count = 0
        errors = []
        
        for token_symbol, indicator_data in results.items():
            if token_symbol == "_summary":
                continue
                
            try:
                if indicator_data is not None:
                    await IndicatorCache.cache_indicators(token_symbol, indicator_data)
                    cached_count += 1
                else:
                    errors.append(f"No data calculated for {token_symbol}")
            except Exception as e:
                error_msg = f"Error caching {token_symbol}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        summary = results.get('_summary', {})
        summary['cached_count'] = cached_count
        summary['cache_errors'] = errors
        
        logger.info(f"Manually refreshed indicators: {cached_count} tokens cached, {len(errors)} errors")
        
        return {
            "message": "Indicators refreshed successfully",
            "summary": summary,
            "cached_count": cached_count,
            "errors": errors,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error manually refreshing indicators: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error refreshing indicators: {str(e)}"
        )


@router.get("/indicators/cache-stats", dependencies=[Depends(get_current_active_user)])
async def get_indicator_cache_stats():
    """Get statistics about the indicator cache (requires authentication)"""
    try:
        stats = await IndicatorCache.get_stats()
        return {
            **stats,
            "refresh_method": "On-demand via refresh endpoint",
            "refresh_endpoint": "POST /indicators/indicators/refresh"
        }
    except Exception as e:
        logger.error(f"Error getting indicator cache stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving cache statistics: {str(e)}"
        )