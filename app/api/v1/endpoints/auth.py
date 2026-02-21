from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from datetime import datetime, timedelta
from jose import jwt
from ....core.deps import authenticate_user, create_user
from ....core.config import settings
from ....models.schemas import Token, UserCreate

router = APIRouter()
security = HTTPBasic()


def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


@router.post("/login", response_model=Token)
async def login(credentials: HTTPBasicCredentials = Depends(security)):
    """Login with username and password to get access token"""
    user = await authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@router.post("/register")
async def register(user_data: UserCreate):
    """Register a new user (for initial setup)"""
    user = await create_user(user_data.username, user_data.password, user_data.full_name)
    return {"message": f"User {user_data.username} created successfully"}