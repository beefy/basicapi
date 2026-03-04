"""
Migration: Create candlestick data indexes
Created: 2026-03-04
"""

from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import os


async def up():
    """Create indexes for candlestick data collection"""
    
    # Connect to MongoDB
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name = os.getenv("DATABASE_NAME", "basicapi")
    
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    
    try:
        print("Creating candlestick data indexes...")
        
        # Composite index on token_symbol and timestamp for efficient time-based queries
        await db.candlestick_data.create_index([
            ("token_symbol", 1),
            ("timestamp", 1)
        ])
        print("✅ Created index: token_symbol + timestamp")
        
        # Unique index on token_address and unix_time to prevent duplicates
        await db.candlestick_data.create_index([
            ("token_address", 1),
            ("unix_time", 1)
        ], unique=True)
        print("✅ Created unique index: token_address + unix_time")
        
        # Index on candle type for filtering
        await db.candlestick_data.create_index("type")
        print("✅ Created index: type")
        
        # Index on created_at for data management
        await db.candlestick_data.create_index("created_at")
        print("✅ Created index: created_at")
        
        # TTL index to automatically delete old data after 6 months (optional)
        # Uncomment the following if you want automatic cleanup:
        # await db.candlestick_data.create_index("created_at", expireAfterSeconds=15552000)  # 6 months
        # print("✅ Created TTL index: created_at (6 months expiry)")
        
        print("🎉 Successfully created all candlestick data indexes")
        
    except Exception as e:
        print(f"❌ Error creating indexes: {e}")
        raise
    finally:
        client.close()


async def down():
    """Remove candlestick data indexes"""
    
    # Connect to MongoDB
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name = os.getenv("DATABASE_NAME", "basicapi")
    
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    
    try:
        print("Removing candlestick data indexes...")
        
        # Get all indexes
        indexes = await db.candlestick_data.list_indexes().to_list(length=None)
        
        for index in indexes:
            index_name = index.get('name')
            if index_name != '_id_':  # Don't drop the default _id index
                await db.candlestick_data.drop_index(index_name)
                print(f"✅ Dropped index: {index_name}")
        
        print("🎉 Successfully removed candlestick data indexes")
        
    except Exception as e:
        print(f"❌ Error removing indexes: {e}")
        raise
    finally:
        client.close()


if __name__ == "__main__":
    print("🔧 Candlestick Data Indexes Migration")
    print("Run with 'up' to create indexes or 'down' to remove them")
    
    import sys
    
    if len(sys.argv) != 2 or sys.argv[1] not in ['up', 'down']:
        print("Usage: python 20260304_000003_candlestick_indexes.py <up|down>")
        exit(1)
    
    action = sys.argv[1]
    
    if action == 'up':
        asyncio.run(up())
    else:
        asyncio.run(down())