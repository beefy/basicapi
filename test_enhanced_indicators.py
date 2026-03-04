#!/usr/bin/env python3
"""
Test script for enhanced indicators with MongoDB integration
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add the app directory to Python path
sys.path.append('/Users/nate/Code/basicapi')

from app.core.indicators import BirdeyeDataFetcher, IndicatorCalculator, TOKEN_ADDRESSES
from app.db.mongodb import connect_to_mongo, close_mongo_connection, get_database


async def test_enhanced_fetcher():
    """Test the enhanced data fetching with MongoDB"""
    
    # Set up database connection
    await connect_to_mongo()
    database = await get_database()
    
    # Initialize components
    fetcher = BirdeyeDataFetcher(database)
    calculator = IndicatorCalculator(database)
    
    try:
        # Test with SOL token
        test_token = "SOL"
        test_address = TOKEN_ADDRESSES[test_token]
        
        print(f"\n📊 Testing enhanced data fetcher with {test_token}")
        print(f"Token address: {test_address}")
        print("=" * 60)
        
        # First run - should fetch most data from API
        print("\n🔄 First run (should fetch most data from API)...")
        start_time = datetime.now()
        
        df1 = await fetcher.get_historical_hourly(test_address, test_token, hours=24)
        
        elapsed_1 = (datetime.now() - start_time).total_seconds()
        print(f"✅ Fetched {len(df1)} data points in {elapsed_1:.2f} seconds")
        print(f"Data range: {df1.index[0]} to {df1.index[-1]}")
        
        # Second run - should use mostly cached data
        print("\n⚡ Second run (should use mostly cached data)...")
        start_time = datetime.now()
        
        df2 = await fetcher.get_historical_hourly(test_address, test_token, hours=24)
        
        elapsed_2 = (datetime.now() - start_time).total_seconds()
        print(f"✅ Fetched {len(df2)} data points in {elapsed_2:.2f} seconds")
        print(f"Data range: {df2.index[0]} to {df2.index[-1]}")
        
        # Calculate speedup
        if elapsed_2 > 0:
            speedup = elapsed_1 / elapsed_2
            print(f"🚀 Speedup: {speedup:.1f}x faster")
        
        # Test indicator calculation
        print("\n📈 Testing indicator calculation...")
        indicators = await calculator.update_token_data(test_token, test_address, fetcher)
        
        print("✅ Calculated indicators:")
        for key, value in indicators.items():
            if isinstance(value, (int, float)):
                print(f"  {key}: {value}")
            elif isinstance(value, str) and len(value) < 50:
                print(f"  {key}: {value}")
        
        # Check database contents
        print("\n💾 Checking database contents...")
        count = await database.candlestick_data.count_documents({"token_address": test_address})
        print(f"✅ {count} candlestick records stored for {test_token}")
        
        # Get latest record
        latest_record = await database.candlestick_data.find_one(
            {"token_address": test_address},
            sort=[("unix_time", -1)]
        )
        if latest_record:
            latest_time = datetime.fromtimestamp(latest_record['unix_time'])
            print(f"  Latest record: {latest_time} (${latest_record['close']:.6f})")
        
        print("\n🎉 Enhanced indicators test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Close database connection
        await close_mongo_connection()


async def test_efficiency_comparison():
    """Test the efficiency gains from MongoDB caching"""
    
    print("\n🔬 Testing efficiency comparison...")
    print("=" * 60)
    
    await connect_to_mongo()
    database = await get_database()
    
    try:
        fetcher = BirdeyeDataFetcher(database)
        test_address = TOKEN_ADDRESSES["JUP"]  # Use JUP for variety
        
        # Clear existing data for this test
        result = await database.candlestick_data.delete_many({"token_address": test_address})
        print(f"🧹 Cleared {result.deleted_count} existing records")
        
        # Test 1: Fresh fetch (no cache)
        print("\n📥 Test 1: Fresh fetch (no cache)")
        start = datetime.now()
        df1 = await fetcher.get_historical_hourly(test_address, "JUP", hours=48)
        time1 = (datetime.now() - start).total_seconds()
        print(f"  Time: {time1:.2f}s, Data points: {len(df1)}")
        
        # Test 2: Mostly cached (extending by 1 hour)
        print("\n⚡ Test 2: Mostly cached (extending by 1 hour)")
        start = datetime.now()
        df2 = await fetcher.get_historical_hourly(test_address, "JUP", hours=48)
        time2 = (datetime.now() - start).total_seconds()
        print(f"  Time: {time2:.2f}s, Data points: {len(df2)}")
        
        # Test 3: Fully cached
        print("\n💨 Test 3: Fully cached")
        start = datetime.now()
        df3 = await fetcher.get_historical_hourly(test_address, "JUP", hours=24)  # Subset of cached data
        time3 = (datetime.now() - start).total_seconds()
        print(f"  Time: {time3:.2f}s, Data points: {len(df3)}")
        
        print(f"\n📊 Results Summary:")
        print(f"  Fresh fetch: {time1:.2f}s")
        print(f"  Mostly cached: {time2:.2f}s ({time1/time2:.1f}x speedup)")
        print(f"  Fully cached: {time3:.2f}s ({time1/time3:.1f}x speedup)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    print("🚀 Starting Enhanced Indicators Test")
    print("Make sure you have BIRDEYE_API_KEY set in your environment")
    
    if not os.getenv("BIRDEYE_API_KEY"):
        print("❌ BIRDEYE_API_KEY environment variable not set!")
        exit(1)
    
    # Run the tests
    asyncio.run(test_enhanced_fetcher())
    print("\n" + "="*80)
    asyncio.run(test_efficiency_comparison())