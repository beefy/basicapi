import pytest
import asyncio
from httpx import AsyncClient
from app.main import app
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


@pytest.fixture(scope=\"session\")
def event_loop():
    \"\"\"Create an instance of the default event loop for the test session.\"\"\"
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope=\"session\")
async def setup_test_db():
    \"\"\"Setup test database\"\"\"
    # Use a test database
    original_db = settings.database_name
    settings.database_name = \"basicapi_test\"
    
    # Connect to test database
    await connect_to_mongo()
    
    yield
    
    # Cleanup: Drop test database and close connection
    client = AsyncIOMotorClient(settings.mongodb_url)
    await client.drop_database(\"basicapi_test\")
    await close_mongo_connection()
    
    # Restore original database name
    settings.database_name = original_db


@pytest.fixture
async def client(setup_test_db):
    \"\"\"Create test client\"\"\"
    async with AsyncClient(app=app, base_url=\"http://test\") as ac:
        yield ac


@pytest.fixture
async def auth_headers(client):
    \"\"\"Get authentication headers\"\"\"
    # Login to get token
    response = await client.post(
        \"/api/v1/auth/token\",
        auth=(\"admin\", \"secret\")
    )
    assert response.status_code == 200
    token = response.json()[\"access_token\"]
    return {\"Authorization\": f\"Bearer {token}\"}
