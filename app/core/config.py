from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "basicapi"
    
    # Security
    secret_key: str
    bootstrap_secret: str = "change-this-bootstrap-secret-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # API
    api_v1_str: str = "/api/v1"
    project_name: str = "BasicAPI"
    
    # GCP
    gcp_project_id: Optional[str] = None
    gcp_region: str = "us-central1"
    
    class Config:
        env_file = ".env"


settings = Settings()
