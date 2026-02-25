# Caching System and Technical Indicators

## Overview

The BasicAPI now includes a MongoDB-based caching system and technical indicator calculation functionality. This replaces the previous in-memory caching to improve scalability and cost-effectiveness in Cloud Run environments.

## New Features Added

### 1. MongoDB-Based Caching System

**Location**: `app/core/cache.py`

- **Price Cache**: Stores cryptocurrency prices with 1-hour TTL
- **Wallet Cache**: Stores wallet balance data with 1-hour TTL  
- **Indicator Cache**: Stores technical indicators with 24-hour TTL

**Benefits over in-memory caching**:
- Shared cache across all Cloud Run instances
- Persistent cache that survives scaling to zero
- Reduced memory usage per instance
- Consistent cache updates visible to all instances

### 2. Technical Indicators

**Location**: `app/core/indicators.py`

Calculates 6 technical indicators for 16 supported tokens:
- **RSI** (14-period): Relative Strength Index
- **Moving Average Cross** (20/50 period): Bull/Bear/Neutral signals
- **Volume Ratio**: Current volume vs 24-hour average
- **ADX** (14-period): Average Directional Index
- **MACD**: Moving Average Convergence Divergence with signals
- **Stochastic Oscillator** (14-period): %K and %D with signals

**Supported Tokens**: SOL, USDC, JUP, PYTH, RAY, JTO, BONK, WIF, ORCA, SRM, STEP, FIDA, COPE, SAMO, MNGO, ATLAS

### 3. Authenticated Indicator API

**Endpoint**: `/v1/indicators/indicators`
**Authentication**: Required (Bearer token)

Returns cached indicator data updated hourly by the cron job.

**Additional endpoints**:
- `POST /v1/indicators/indicators/refresh` - Manual indicator refresh
- `GET /v1/indicators/cache-stats` - Cache statistics

### 4. Automated Hourly Updates

**Cron Job Service**: `basicapi-indicator-cron`
**Schedule**: Every hour on the hour (0 * * * *)
**Implementation**: Separate Cloud Run service triggered by Google Cloud Scheduler

## Database Changes

### Migration: `20260225_000002_create_cache_collections.py`

Creates three MongoDB collections with automatic TTL expiration:
- `price_cache` - 2-hour TTL with unique index on token_address
- `wallet_cache` - 2-hour TTL with unique index on wallet_address  
- `indicator_cache` - 25-hour TTL with unique index on token_symbol

## Updated API Endpoints

### Wallet Endpoints (Modified)

- `GET /v1/wallet/balances` - Now uses MongoDB cache
- `GET /v1/wallet/cache-stats` - Updated for MongoDB cache stats

### New Indicator Endpoints

- `GET /v1/indicators/indicators` - Get cached technical indicators (auth required)
- `POST /v1/indicators/indicators/refresh` - Manually refresh indicators (auth required)
- `GET /v1/indicators/cache-stats` - Get indicator cache statistics (auth required)

## Environment Variables

The following environment variables are required for the new functionality:

```bash
# Existing (unchanged)
MONGODB_URL=mongodb://...
DATABASE_NAME=your_database
BIRDEYE_API_KEY=your_api_key

# For authentication
SECRET_KEY=your_secret_key
ALLOWED_USER_1=username1
ALLOWED_USER_2=username2  
ALLOWED_USER_3=username3
```

## Deployment

### Main API Service
The existing deployment process handles the main API with updated caching.

### Cron Job Service  
A separate Cloud Run service is deployed for indicator updates:

```bash
# Automatic deployment via GitHub Actions
# Triggers on changes to:
# - cron_jobs/**
# - app/core/indicators.py
# - app/core/cache.py
# - Dockerfile.cron
```

### Google Cloud Scheduler
Automatically configured to trigger the cron job hourly:
- **Job Name**: `indicator-refresh-job`
- **Schedule**: `0 * * * *` (every hour on the hour)
- **Target**: Cloud Run service via HTTP POST
- **Authentication**: OIDC with service account

## Monitoring

### Cache Statistics
- Monitor cache hit rates and entry counts via `/v1/wallet/cache-stats`
- Monitor indicator cache via `/v1/indicators/cache-stats`

### Cron Job Monitoring
- Cloud Run logs for the `basicapi-indicator-cron` service
- Cloud Scheduler execution history
- Detailed response logging in cron job executions

### Performance Benefits
- Reduced API calls to external services (Birdeye, Solana RPC)
- Lower Cloud Run costs due to shared caching
- Faster response times for cached data
- Improved reliability with automatic cache expiration

## API Usage Examples

### Get Technical Indicators
```bash
# First, get authentication token
curl -X POST "https://your-api-url/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'

# Use the token to get indicators
curl -X GET "https://your-api-url/v1/indicators/indicators" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Response Format
```json
{
  "indicators": {
    "SOL": {
      "token_symbol": "SOL",
      "rsi": 65.2,
      "ma_cross": "bull",
      "volume_ratio": 1.8,
      "adx": 28.5,
      "macd": "bull",
      "stochastic_signal": "neutral",
      "current_price": 98.45,
      "timestamp": "2026-02-25T10:00:00Z"
    }
  },
  "summary": {
    "total_tokens": 16,
    "successful": 15,
    "failed": 1
  },
  "cached_at": "2026-02-25T10:00:00Z",
  "cache_age_minutes": 25
}
```

## Migration Steps

1. **Run Database Migration**:
   ```bash
   python migrate.py
   ```

2. **Deploy Updated API**:
   ```bash
   git push origin main  # Triggers automatic deployment
   ```

3. **Deploy Cron Job Service**:
   ```bash
   # Automatic via GitHub Actions when cron_jobs/ changes are pushed
   ```

4. **Verify Deployment**:
   - Check that cache collections exist in MongoDB
   - Verify cron job service is deployed
   - Confirm Cloud Scheduler job is created
   - Test indicator endpoints with authentication

The system is designed to be backward compatible - existing wallet endpoints continue to work with improved performance through MongoDB caching.