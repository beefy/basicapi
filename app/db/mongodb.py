from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from ..core.config import settings


class Database:
    client: Optional[AsyncIOMotorClient] = None
    database = None


db = Database()


async def get_database():
    return db.database


async def connect_to_mongo():
    """Create database connection"""
    db.client = AsyncIOMotorClient(settings.mongodb_url)
    db.database = db.client[settings.database_name]
    
    # Create indexes for performance
    await create_indexes()


async def close_mongo_connection():
    """Close database connection"""
    if db.client:
        db.client.close()


async def create_indexes():
    """Create database indexes for performance"""
    if not db.database:
        return
        
    # Status updates indexes
    await db.database.status_updates.create_index("agent_name")
    await db.database.status_updates.create_index("timestamp")
    
    # Responses indexes
    await db.database.responses.create_index("agent_name")
    await db.database.responses.create_index("received_ts")
    
    # System info indexes
    await db.database.system_info.create_index("agent_name")
    await db.database.system_info.create_index("ts")
    
    # Heartbeat indexes (unique on agent_name for upsert behavior)
    await db.database.heartbeat.create_index("agent_name", unique=True)
