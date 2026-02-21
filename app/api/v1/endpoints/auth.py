from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from datetime import timedelta
from ...core.security import verify_password, create_access_token
from ...core.deps import fake_users_db
from ...models.schemas import Token

router = APIRouter()
security = HTTPBasic()


@router.post(\"/token\", response_model=Token)
async def login_for_access_token(credentials: HTTPBasicCredentials = Depends(security)):
    \"\"\"Authenticate and get access token\"\"\"
    user_dict = fake_users_db.get(credentials.username)
    if not user_dict or not verify_password(credentials.password, user_dict[\"hashed_password\"]):
        raise HTTPException(
            status_code=400,
            detail=\"Incorrect username or password\"
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        subject=credentials.username, expires_delta=access_token_expires
    )
    return {\"access_token\": access_token, \"token_type\": \"bearer\"}
