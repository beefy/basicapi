import pytest
from datetime import datetime


@pytest.mark.asyncio
async def test_root(client):
    """Test root endpoint"""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "Welcome to BasicAPI"


@pytest.mark.asyncio
async def test_health(client):
    """Test health endpoint"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_login(client):
    """Test authentication"""
    response = await client.post(
        "/api/v1/auth/token",
        auth=("admin", "secret")
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid(client):
    """Test authentication with invalid credentials"""
    response = await client.post(
        "/api/v1/auth/token",
        auth=("admin", "wrong_password")
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_status_updates_crud(client, auth_headers):
    """Test status updates CRUD operations"""
    # Create status update
    status_data = {
        "agent_name": "test_agent",
        "update_text": "Test update",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    response = await client.post(
        "/api/v1/status-updates/",
        json=status_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    created_status = response.json()
    assert created_status["agent_name"] == status_data["agent_name"]
    
    # Get status updates
    response = await client.get("/api/v1/status-updates/")
    assert response.status_code == 200
    status_list = response.json()
    assert len(status_list) > 0
    assert any(s["agent_name"] == "test_agent" for s in status_list)


@pytest.mark.asyncio
async def test_heartbeat_upsert(client, auth_headers):
    """Test heartbeat upsert behavior"""
    heartbeat_data = {
        "agent_name": "test_agent",
        "last_heartbeat_ts": datetime.utcnow().isoformat()
    }
    
    # Create first heartbeat
    response = await client.post(
        "/api/v1/heartbeat/",
        json=heartbeat_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    first_heartbeat = response.json()
    
    # Create second heartbeat for same agent (should update, not create new)
    heartbeat_data["last_heartbeat_ts"] = datetime.utcnow().isoformat()
    response = await client.post(
        "/api/v1/heartbeat/",
        json=heartbeat_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    second_heartbeat = response.json()
    
    # Get all heartbeats - should only have one for this agent
    response = await client.get("/api/v1/heartbeat/?agent_name=test_agent")
    assert response.status_code == 200
    heartbeats = response.json()
    assert len(heartbeats) == 1  # Only one heartbeat per agent


@pytest.mark.asyncio
async def test_unauthorized_access(client):
    """Test that endpoints requiring authentication return 401 without auth"""
    status_data = {
        "agent_name": "test_agent",
        "update_text": "Test update"
    }
    
    response = await client.post("/api/v1/status-updates/", json=status_data)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_response_time_stats(client, auth_headers):
    """Test response time statistics"""
    # Create some response time data
    response_data = {
        "agent_name": "test_agent",
        "received_ts": "2024-01-01T10:00:00",
        "sent_ts": "2024-01-01T10:00:01"
    }
    
    response = await client.post(
        "/api/v1/response-times/",
        json=response_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    
    # Get statistics
    response = await client.get("/api/v1/response-times/stats")
    assert response.status_code == 200
    stats = response.json()
    assert len(stats) > 0
    assert any(s["agent_name"] == "test_agent" for s in stats)
