from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .api.v1.api import api_router
from .db.mongodb import connect_to_mongo, close_mongo_connection


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.project_name,
        version="1.0.0",
        description="BasicAPI - A FastAPI application for monitoring agent data",
        openapi_url=f"{settings.api_v1_str}/openapi.json"
    )
    
    # Set up CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API router
    application.include_router(api_router, prefix=settings.api_v1_str)
    
    # Add startup and shutdown events
    application.add_event_handler("startup", connect_to_mongo)
    application.add_event_handler("shutdown", close_mongo_connection)
    
    return application


app = create_application()


@app.get("/")
async def root():
    return {"message": "Welcome to BasicAPI", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
