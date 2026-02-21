from fastapi import APIRouter
from .endpoints import (
    status_updates,
    system_info,
    response_times,
    heartbeat,
    api_keys,
    bootstrap
)

api_router = APIRouter()
api_router.include_router(bootstrap.router, prefix="/bootstrap", tags=["bootstrap"])
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["api-keys"])
api_router.include_router(status_updates.router, prefix="/status-updates", tags=["status-updates"])
api_router.include_router(system_info.router, prefix="/system-info", tags=["system-info"])
api_router.include_router(response_times.router, prefix="/response-times", tags=["response-times"])
api_router.include_router(heartbeat.router, prefix="/heartbeat", tags=["heartbeat"])
