"""
Migration: Create balances table
Created: 2026-03-04
Description: Creates the balances collection with indexes for efficient querying
"""

from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import os


async def up():
    """Create balances collection and indexes"""
    
    # Connect to MongoDB
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name = os.getenv("DATABASE_NAME", "basicapi")
    
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    
    try:
        print("Creating balances collection and indexes...")
        
        # Composite index on agent_name and timestamp for efficient agent-specific queries
        await db.balances.create_index([
            ("agent_name", 1),
            ("timestamp", -1)  # Descending for latest first
        ])
        print("✅ Created index: agent_name + timestamp")
        
        # Index on token_name for token-specific queries
        await db.balances.create_index("token_name")
        print("✅ Created index: token_name")
        
        # Composite index for agent and token combination
        await db.balances.create_index([
            ("agent_name", 1),
            ("token_name", 1),
            ("timestamp", -1)
        ])
        print("✅ Created index: agent_name + token_name + timestamp")
        
        # Index on timestamp for time-based queries
        await db.balances.create_index("timestamp")
        print("✅ Created index: timestamp")
        
        print("✅ Balances collection setup completed!")
        
    except Exception as e:
        print(f"❌ Error creating balances indexes: {e}")
        raise e
    finally:
        client.close()


async def down():
    """Drop balances collection"""
    
    # Connect to MongoDB
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name = os.getenv("DATABASE_NAME", "basicapi")
    
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    
    try:
        print("Dropping balances collection...")
        await db.balances.drop()
        print("✅ Balances collection dropped!")
        
    except Exception as e:
        print(f"❌ Error dropping balances collection: {e}")
        raise e
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(up())