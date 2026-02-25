"""Create cache collections for price, wallet, and indicator caching

Created: 2026-02-25T00:00:00
"""

from datetime import datetime, timedelta


def upgrade(db):
    """Apply migration changes"""
    
    # Create price_cache collection with TTL index
    # Documents will automatically expire after 2 hours (1 hour cache + 1 hour buffer)
    db.price_cache.create_index("expires_at", expireAfterSeconds=0)
    db.price_cache.create_index("token_address", unique=True)
    
    # Create wallet_cache collection with TTL index
    # Documents will automatically expire after 2 hours (1 hour cache + 1 hour buffer)
    db.wallet_cache.create_index("expires_at", expireAfterSeconds=0)
    db.wallet_cache.create_index("wallet_address", unique=True)
    
    # Create indicator_cache collection with TTL index
    # Documents will automatically expire after 25 hours (24 hour cache + 1 hour buffer)
    db.indicator_cache.create_index("expires_at", expireAfterSeconds=0)
    db.indicator_cache.create_index("token_symbol", unique=True)
    
    # Create indexes for performance
    db.price_cache.create_index("updated_at")
    db.wallet_cache.create_index("updated_at")
    db.indicator_cache.create_index("updated_at")
    
    print("Created cache collections with TTL indexes")


def downgrade(db):
    """Rollback migration changes"""
    try:
        # Drop the collections (this will also drop all indexes)
        db.price_cache.drop()
        db.wallet_cache.drop() 
        db.indicator_cache.drop()
        print("Dropped cache collections")
    except Exception as e:
        print(f"Error dropping cache collections: {e}")