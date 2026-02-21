from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "basicapi"
    
    # Security
    secret_key: str
    allowed_user_1: str = ""
    allowed_user_2: str = ""
    allowed_user_3: str = ""
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
    
    def get_allowed_usernames(self) -> list:
        """Get list of allowed usernames from individual environment variables"""
        usernames = []
        for user in [self.allowed_user_1, self.allowed_user_2, self.allowed_user_3]:
            if user.strip():
                usernames.append(user.strip())
        return usernames


settings = Settings()
