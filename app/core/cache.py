"""MongoDB-based cache system for price, wallet, and indicator data"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from motor.motor_asyncio import AsyncIOMotorCollection
import logging
from ..db.mongodb import get_database

logger = logging.getLogger(__name__)

class MongoCache:
    """MongoDB-based cache with TTL support"""
    
    @staticmethod
    async def get_collection(collection_name: str) -> AsyncIOMotorCollection:
        """Get MongoDB collection"""
        db = await get_database()
        return db[collection_name]

    @staticmethod
    async def set_cache(collection_name: str, key: str, value: Any, ttl_hours: int = 1) -> bool:
        """Set cache value with TTL"""
        try:
            collection = await MongoCache.get_collection(collection_name)
            now = datetime.utcnow()
            expires_at = now + timedelta(hours=ttl_hours)
            
            cache_doc = {
                "key": key,
                "value": value,
                "updated_at": now,
                "expires_at": expires_at
            }
            
            # Upsert the document
            await collection.replace_one(
                {"key": key}, 
                cache_doc, 
                upsert=True
            )
            
            logger.debug(f"Cached {key} in {collection_name} (expires: {expires_at})")
            return True
            
        except Exception as e:
            logger.error(f"Error setting cache for {key}: {str(e)}")
            return False

    @staticmethod  
    async def get_cache(collection_name: str, key: str) -> Optional[Any]:
        """Get cache value if still valid"""
        try:
            collection = await MongoCache.get_collection(collection_name)
            
            # Find document that hasn't expired
            now = datetime.utcnow()
            doc = await collection.find_one({
                "key": key,
                "expires_at": {"$gt": now}
            })
            
            if doc:
                logger.debug(f"Cache hit for {key} in {collection_name}")
                return doc["value"]
            else:
                logger.debug(f"Cache miss for {key} in {collection_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting cache for {key}: {str(e)}")
            return None

    @staticmethod
    async def delete_cache(collection_name: str, key: str) -> bool:
        """Delete cache entry"""
        try:
            collection = await MongoCache.get_collection(collection_name)
            result = await collection.delete_one({"key": key})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting cache for {key}: {str(e)}")
            return False

    @staticmethod
    async def get_cache_stats(collection_name: str) -> Dict:
        """Get cache statistics"""
        try:
            collection = await MongoCache.get_collection(collection_name)
            now = datetime.utcnow()
            
            # Count total entries
            total_entries = await collection.count_documents({})
            
            # Count valid entries (not expired)
            valid_entries = await collection.count_documents({
                "expires_at": {"$gt": now}
            })
            
            # Count expired entries
            expired_entries = total_entries - valid_entries
            
            # Get oldest and newest entries
            pipeline = [
                {"$match": {"expires_at": {"$gt": now}}},
                {"$group": {
                    "_id": None,
                    "oldest": {"$min": "$updated_at"},
                    "newest": {"$max": "$updated_at"}
                }}
            ]
            
            age_stats = await collection.aggregate(pipeline).to_list(1)
            oldest = age_stats[0]["oldest"] if age_stats else None
            newest = age_stats[0]["newest"] if age_stats else None
            
            return {
                "collection": collection_name,
                "total_entries": total_entries,
                "valid_entries": valid_entries,
                "expired_entries": expired_entries,
                "oldest_entry": oldest,
                "newest_entry": newest,
                "timestamp": now
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats for {collection_name}: {str(e)}")
            return {
                "collection": collection_name,
                "error": str(e),
                "timestamp": datetime.utcnow()
            }

    @staticmethod
    async def cleanup_expired(collection_name: str) -> int:
        """Remove expired entries manually (normally handled by TTL)"""
        try:
            collection = await MongoCache.get_collection(collection_name)
            now = datetime.utcnow()
            
            result = await collection.delete_many({
                "expires_at": {"$lte": now}
            })
            
            if result.deleted_count > 0:
                logger.info(f"Cleaned up {result.deleted_count} expired entries from {collection_name}")
            
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired cache in {collection_name}: {str(e)}")
            return 0


class PriceCache:
    """Price caching using MongoDB"""
    COLLECTION = "price_cache"
    TTL_HOURS = 1
    
    @staticmethod
    async def get_cached_price(token_address: str) -> Optional[float]:
        """Get cached price if still valid"""
        cached_data = await MongoCache.get_cache(PriceCache.COLLECTION, token_address)
        if cached_data is not None:
            logger.debug(f"Using cached price for {token_address}: ${cached_data}")
            return cached_data
        return None
    
    @staticmethod
    async def cache_price(token_address: str, price: Optional[float]) -> None:
        """Cache a price with TTL"""
        await MongoCache.set_cache(
            PriceCache.COLLECTION, 
            token_address, 
            price, 
            PriceCache.TTL_HOURS
        )
        logger.debug(f"Cached price for {token_address}: ${price}")
    
    @staticmethod
    async def get_stats() -> Dict:
        """Get price cache statistics"""
        return await MongoCache.get_cache_stats(PriceCache.COLLECTION)


class WalletCache:
    """Wallet caching using MongoDB"""
    COLLECTION = "wallet_cache"
    TTL_HOURS = 1
    
    @staticmethod
    async def get_cached_wallet_data(wallet_address: str) -> Optional[tuple]:
        """Get cached wallet data if still valid"""
        cached_data = await MongoCache.get_cache(WalletCache.COLLECTION, wallet_address)
        if cached_data is not None:
            logger.debug(f"Using cached wallet data for {wallet_address[:8]}...")
            return (
                cached_data['balances'],
                cached_data['total_value'], 
                cached_data['transactions']
            )
        return None
    
    @staticmethod
    async def cache_wallet_data(wallet_address: str, balances: Dict, total_value: float, transactions: List) -> None:
        """Cache wallet data with TTL"""
        cache_value = {
            'balances': balances,
            'total_value': total_value,
            'transactions': transactions
        }
        
        await MongoCache.set_cache(
            WalletCache.COLLECTION,
            wallet_address,
            cache_value,
            WalletCache.TTL_HOURS
        )
        logger.info(f"Cached wallet data for {wallet_address[:8]}... with total value: ${total_value:.2f}")
    
    @staticmethod
    async def get_stats() -> Dict:
        """Get wallet cache statistics"""
        return await MongoCache.get_cache_stats(WalletCache.COLLECTION)


class IndicatorCache:
    """Indicator caching using MongoDB"""
    COLLECTION = "indicator_cache"
    TTL_HOURS = 24  # 24-hour cache for indicators
    
    @staticmethod
    async def get_cached_indicators(token_symbol: str) -> Optional[Dict]:
        """Get cached indicator data if still valid"""
        cached_data = await MongoCache.get_cache(IndicatorCache.COLLECTION, token_symbol)
        if cached_data is not None:
            logger.debug(f"Using cached indicators for {token_symbol}")
            return cached_data
        return None
    
    @staticmethod
    async def cache_indicators(token_symbol: str, indicators: Dict) -> None:
        """Cache indicator data with TTL"""
        await MongoCache.set_cache(
            IndicatorCache.COLLECTION,
            token_symbol,
            indicators,
            IndicatorCache.TTL_HOURS
        )
        logger.info(f"Cached indicators for {token_symbol}")
    
    @staticmethod
    async def get_all_cached_indicators() -> Dict[str, Dict]:
        """Get all cached indicators"""
        try:
            collection = await MongoCache.get_collection(IndicatorCache.COLLECTION)
            now = datetime.utcnow()
            
            # Get all valid (non-expired) indicators
            cursor = collection.find({
                "expires_at": {"$gt": now}
            })
            
            result = {}
            async for doc in cursor:
                result[doc["key"]] = doc["value"]
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting all cached indicators: {str(e)}")
            return {}
    
    @staticmethod
    async def get_stats() -> Dict:
        """Get indicator cache statistics"""
        return await MongoCache.get_cache_stats(IndicatorCache.COLLECTION)