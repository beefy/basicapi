# BasicAPI

A comprehensive FastAPI application for monitoring and storing agent data with MongoDB backend, device fingerprinting authentication, and automated deployment to Google Cloud Platform. Perfect for secure Raspberry Pi monitoring with dynamic IP addresses.

## Setup
```
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

For local mongodb setup
```
# Install MongoDB Community Edition
brew tap mongodb/brew
brew install mongodb-community

# Start MongoDB as a service (runs in background)
brew services start mongodb/brew/mongodb-community

# Or start manually (runs in foreground)
mongod --config /opt/homebrew/etc/mongod.conf
```

## Features

- **RESTful API** built with FastAPI
- **MongoDB** for data storage with async support
- **API Key Authentication** with device fingerprinting for security
- **Automated Testing** with pytest
- **Database Migrations** with pymongo-migrate
- **Docker Containerization**
- **CI/CD Pipeline** with GitHub Actions
- **GCP Cloud Run Deployment**

## API Endpoints

### Bootstrap (Admin Setup)
- `POST /api/v1/bootstrap/admin-key` - Create first admin key (localhost only, requires bootstrap secret)

### Admin Management  
- `POST /api/v1/admin/device-key` - Create device API keys (requires admin key)
- `GET /api/v1/admin/keys` - List all API keys (requires admin key)
- `DELETE /api/v1/admin/keys/{key_id}` - Delete API key (requires admin key)

### Status Updates
- `GET /api/v1/status-updates/` - Query status updates
- `POST /api/v1/status-updates/` - Store status update (requires device key)

### System Information
- `GET /api/v1/system-info/` - Query system information
- `POST /api/v1/system-info/` - Store system info (requires device key)

### Response Times
- `GET /api/v1/response-times/stats` - Get average response time statistics
- `POST /api/v1/response-times/` - Store response time data (requires device key)

### Heartbeats
- `GET /api/v1/heartbeat/` - Query heartbeats
- `POST /api/v1/heartbeat/` - Store/update heartbeat (requires auth, upsert behavior)

## Data Models

### Status Updates
```json
{
  "agent_name": "string",
  "update_text": "string",
  "timestamp": "2024-01-01T10:00:00Z"
}
```

### System Information
```json
{
  "agent_name": "string",
  "cpu": 75.5,
  "memory": 60.2,
  "disk": 45.1,
  "ts": "2024-01-01T10:00:00Z"
}
```

### Response Times
```json
{
  "agent_name": "string",
  "received_ts": "2024-01-01T10:00:00Z",
  "sent_ts": "2024-01-01T10:00:01Z"
}
```

### Heartbeats
```json
{
  "agent_name": "string",
  "last_heartbeat_ts": "2024-01-01T10:00:00Z"
}
```

## Quick Start

### Prerequisites
- Python 3.11+
- MongoDB
- Docker (optional)
- Google Cloud SDK (for deployment)

### Local Development

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd basicapi
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start MongoDB** (if running locally):
   ```bash
   # Using Docker
   docker run -d -p 27017:27017 --name mongodb mongo:latest
   
   # Or install MongoDB locally
   # macOS: brew install mongodb/brew/mongodb-community
   # Ubuntu: sudo apt install mongodb
   ```

4. **Run migrations**:
   ```bash
   python migrate.py up
   ```

5. **Start the application**:
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Access the API**:
   - API Documentation: http://localhost:8000/docs
   - API: http://localhost:8000/api/v1/
   - Health Check: http://localhost:8000/health

### Using Docker

1. **Build and run**:
   ```bash
   docker build -t basicapi .
   docker run -p 8000:8000 --env-file .env basicapi
   ```

2. **Using Docker Compose** (create docker-compose.yml):
   ```yaml
   version: '3.8'
   services:
     app:
       build: .
       ports:
         - "8000:8000"
       environment:
         - MONGODB_URL=mongodb://mongodb:27017
         - DATABASE_NAME=basicapi
         - SECRET_KEY=your-secret-key
       depends_on:
         - mongodb
     
     mongodb:
       image: mongo:latest
       ports:
         - "27017:27017"
       volumes:
         - mongodb_data:/data/db
   
   volumes:
     mongodb_data:
   ```

## Testing

Run the test suite:
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## Authentication & Setup

The API uses API key authentication with device fingerprinting. Here's how to set it up:

### Security Configuration

The bootstrap endpoint for creating the first admin key is protected in two ways:

1. **Localhost Only**: The bootstrap endpoint only accepts requests from localhost (127.0.0.1) for security
2. **Bootstrap Secret**: You must provide a `bootstrap_secret` in the request body

Set your bootstrap secret in the environment:
```bash
export BOOTSTRAP_SECRET=your-super-secret-bootstrap-key-change-this-in-production
```

### Initial Setup

1. **Create your first admin API key** (must be done from localhost):
   ```bash
   curl -X POST http://localhost:8000/api/v1/bootstrap/admin-key \
     -H "Content-Type: application/json" \
     -d '{"bootstrap_secret": "your-super-secret-bootstrap-key-change-this-in-production"}'
   ```

2. **Create device keys for your Raspberry Pis** using the admin key:
   ```bash
   curl -X POST http://localhost:8000/api/v1/admin/device-key \
     -H "Authorization: Bearer YOUR_ADMIN_KEY" \
     -H "Content-Type: application/json" \
     -d '{"device_name": "pi-livingroom"}'
   ```

### Using Device Keys

All POST endpoints require a device API key. The system automatically validates both the key and device fingerprint:

```bash
curl -X POST "http://localhost:8000/api/v1/status-updates/" \
     -H "Authorization: Bearer YOUR_DEVICE_KEY" \
     -H "Content-Type: application/json" \
     -d '{"agent_name": "test", "update_text": "Hello"}'
```

**Note**: API keys don't expire automatically - they're permanent until you delete them. This is perfect for automated monitoring systems like Raspberry Pis that shouldn't need key rotation.

## Database Migrations

Manage database schema changes with the migration system:

```bash
# Create a new migration
python migrate.py create add_new_index

# Run all pending migrations
python migrate.py up

# Rollback last migration
python migrate.py down

# Check migration status
python migrate.py status
```

## Deployment to Google Cloud Platform

### Prerequisites
1. Google Cloud Project with billing enabled
2. Cloud Run and Artifact Registry APIs enabled
3. Service account with appropriate permissions

### Setup GitHub Secrets

Add these secrets to your GitHub repository:

- `GCP_PROJECT_ID`: Your Google Cloud project ID
- `GCP_SA_KEY`: Service account JSON key (base64 encoded)
- `MONGODB_URL`: MongoDB connection string for production
- `DATABASE_NAME`: Production database name
- `SECRET_KEY`: JWT secret key for production

### Manual Deployment

1. **Build and push to Artifact Registry**:
   ```bash
   # Configure Docker
   gcloud auth configure-docker us-central1-docker.pkg.dev
   
   # Build and push
   docker build -t us-central1-docker.pkg.dev/PROJECT_ID/basicapi/basicapi:latest .
   docker push us-central1-docker.pkg.dev/PROJECT_ID/basicapi/basicapi:latest
   ```

2. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy basicapi \\
     --image=us-central1-docker.pkg.dev/PROJECT_ID/basicapi/basicapi:latest \\
     --region=us-central1 \\
     --allow-unauthenticated \\
     --set-env-vars="MONGODB_URL=your-mongodb-url,DATABASE_NAME=basicapi,SECRET_KEY=your-secret"
   ```

### Automated Deployment

Push to the `main` branch to trigger automatic deployment via GitHub Actions.

## Configuration

Environment variables (copy from `.env.example`):

```bash
# Database
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=basicapi

# Security
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API
API_V1_STR=/api/v1
PROJECT_NAME=BasicAPI

# GCP (for deployment)
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
```

## API Usage Examples

### Store Status Update
```bash
# Get token first
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/token" -u admin:secret | jq -r '.access_token')

# Store status update
curl -X POST "http://localhost:8000/api/v1/status-updates/" \\
     -H "Authorization: Bearer $TOKEN" \\
     -H "Content-Type: application/json" \\
     -d '{
       "agent_name": "web-server-01",
       "update_text": "Service started successfully"
     }'
```

### Query Status Updates
```bash
# Get all status updates
curl "http://localhost:8000/api/v1/status-updates/"

# Filter by agent name
curl "http://localhost:8000/api/v1/status-updates/?agent_name=web-server-01"

# Filter by date range
curl "http://localhost:8000/api/v1/status-updates/?start_date=2024-01-01T00:00:00&end_date=2024-01-02T00:00:00"
```

### Store System Information
```bash
curl -X POST "http://localhost:8000/api/v1/system-info/" \\
     -H "Authorization: Bearer $TOKEN" \\
     -H "Content-Type: application/json" \\
     -d '{
       "agent_name": "web-server-01",
       "cpu": 75.5,
       "memory": 60.2,
       "disk": 45.1
     }'
```

### Get Response Time Statistics
```bash
# Get average response times for all agents
curl "http://localhost:8000/api/v1/response-times/stats"

# Filter by agent
curl "http://localhost:8000/api/v1/response-times/stats?agent_name=web-server-01"
```

## Project Structure

```
basicapi/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── api/
│   │   └── v1/
│   │       ├── api.py          # API router
│   │       └── endpoints/      # Individual endpoint modules
│   ├── core/
│   │   ├── config.py           # Configuration settings
│   │   ├── security.py         # JWT and password utilities
│   │   └── deps.py             # Dependencies and auth
│   ├── db/
│   │   └── mongodb.py          # Database connection
│   └── models/
│       └── schemas.py          # Pydantic models
├── migrations/                 # Database migrations
├── tests/                      # Test files
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions workflow
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── migrate.py                  # Migration management script
├── start.sh                    # Application start script
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
An fastapi api that queries mongodb and is deployed on GCP
