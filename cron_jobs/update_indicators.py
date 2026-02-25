"""
Standalone cron job for refreshing technical indicators.

This script runs as a separate Cloud Run service triggered by Google Cloud Scheduler.
It calculates technical indicators for all supported tokens and caches them in MongoDB.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict

# Add the parent directory to the path so we can import from the main app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.indicators import get_all_token_indicators
from app.core.cache import IndicatorCache
from app.db.mongodb import connect_to_mongo, close_mongo_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def update_indicators():
    """Main function to update all technical indicators"""
    start_time = datetime.utcnow()
    logger.info(f"Starting indicator update job at {start_time.isoformat()}")
    
    try:
        # Connect to MongoDB
        logger.info("Connecting to MongoDB...")
        await connect_to_mongo()
        logger.info("Connected to MongoDB successfully")
        
        # Calculate indicators for all tokens
        logger.info("Calculating technical indicators for all tokens...")
        results = await get_all_token_indicators()
        
        # Cache each token's indicators
        cached_count = 0
        errors = []
        
        for token_symbol, indicator_data in results.items():
            if token_symbol == "_summary":
                # Cache the summary info as well
                try:
                    await IndicatorCache.cache_indicators("_summary", indicator_data)
                except Exception as e:
                    logger.error(f"Error caching summary: {str(e)}")
                continue
                
            try:
                if indicator_data is not None:
                    await IndicatorCache.cache_indicators(token_symbol, indicator_data)
                    cached_count += 1
                    logger.info(f"Cached indicators for {token_symbol}")
                else:
                    error_msg = f"No data calculated for {token_symbol}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
            except Exception as e:
                error_msg = f"Error caching {token_symbol}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Log final results
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        summary = results.get('_summary', {})
        total_tokens = summary.get('total_tokens', 0)
        successful = summary.get('successful', 0)
        failed = summary.get('failed', 0)
        
        logger.info(f"Indicator update completed in {duration:.2f} seconds:")
        logger.info(f"  - Total tokens: {total_tokens}")
        logger.info(f"  - Successful calculations: {successful}")
        logger.info(f"  - Failed calculations: {failed}")
        logger.info(f"  - Cached successfully: {cached_count}")
        logger.info(f"  - Cache errors: {len(errors)}")
        
        if errors:
            logger.warning(f"Errors encountered: {errors}")
        
        # Cache statistics
        try:
            cache_stats = await IndicatorCache.get_stats()
            logger.info(f"Cache stats: {cache_stats['valid_entries']} valid entries, {cache_stats['total_entries']} total")
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
        
        return {
            "success": True,
            "duration_seconds": duration,
            "total_tokens": total_tokens,
            "successful_calculations": successful,
            "failed_calculations": failed,
            "cached_count": cached_count,
            "cache_errors": len(errors),
            "errors": errors,
            "timestamp": end_time.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Critical error in indicator update job: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    finally:
        # Always close the MongoDB connection
        try:
            await close_mongo_connection()
            logger.info("MongoDB connection closed")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {str(e)}")


def main():
    """Entry point for the cron job"""
    try:
        result = asyncio.run(update_indicators())
        
        if result["success"]:
            logger.info("Indicator update job completed successfully")
            print(f"SUCCESS: {result}")
            sys.exit(0)
        else:
            logger.error(f"Indicator update job failed: {result['error']}")
            print(f"ERROR: {result}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Job interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unhandled exception in main: {str(e)}", exc_info=True)
        print(f"CRITICAL ERROR: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()