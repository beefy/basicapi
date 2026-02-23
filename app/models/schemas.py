from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict
from bson import ObjectId


class StatusUpdateBase(BaseModel):
    agent_name: str
    update_text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StatusUpdateCreate(StatusUpdateBase):
    pass


class StatusUpdateResponse(StatusUpdateBase):
    id: Optional[str] = Field(alias="_id", default=None)

    model_config = {
        "populate_by_name": True,
        "json_encoders": {ObjectId: str},
    }


class ResponseTimeBase(BaseModel):
    agent_name: str
    received_ts: datetime
    sent_ts: datetime


class ResponseTimeCreate(ResponseTimeBase):
    pass


class ResponseTimeResponse(ResponseTimeBase):
    id: Optional[str] = Field(alias="_id", default=None)

    model_config = {
        "populate_by_name": True,
        "json_encoders": {ObjectId: str},
    }


class ResponseTimeStats(BaseModel):
    agent_name: str
    average_response_time_ms: float
    count: int


class TokenBalance(BaseModel):
    balance: float
    usd_price: Optional[float] = None
    usd_value: Optional[float] = None


class TokenChange(BaseModel):
    mint: str
    symbol: Optional[str] = None
    change: float
    direction: str  # 'sent' or 'received'


class TransactionInfo(BaseModel):
    signature: str
    block_time: Optional[int] = None
    slot: Optional[int] = None
    confirmation_status: Optional[str] = None
    sol_change: Optional[float] = None
    sol_direction: Optional[str] = None  # 'sent', 'received', or 'none'
    token_changes: List[TokenChange] = []
    program_used: Optional[str] = None
    transaction_type: Optional[str] = None  # 'transfer', 'swap', 'other'


class WalletBalanceItem(BaseModel):
    wallet_address: str
    balances: Dict[str, TokenBalance]
    total_usd_value: Optional[float] = None
    recent_transactions: List[TransactionInfo] = []


class WalletBalanceResponse(BaseModel):
    wallets: List[WalletBalanceItem]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SystemInfoBase(BaseModel):
    agent_name: str
    cpu: float = Field(..., description="CPU usage percentage")
    memory: float = Field(..., description="Memory usage percentage")
    disk: float = Field(..., description="Disk usage percentage")
    ts: datetime = Field(default_factory=datetime.utcnow)


class SystemInfoCreate(SystemInfoBase):
    pass


class SystemInfoResponse(SystemInfoBase):
    id: Optional[str] = Field(alias="_id", default=None)

    model_config = {
        "populate_by_name": True,
        "json_encoders": {ObjectId: str},
    }


class HeartbeatBase(BaseModel):
    agent_name: str
    last_heartbeat_ts: datetime = Field(default_factory=datetime.utcnow)


class HeartbeatCreate(HeartbeatBase):
    pass


class HeartbeatResponse(HeartbeatBase):
    id: Optional[str] = Field(alias="_id", default=None)

    model_config = {
        "populate_by_name": True,
        "json_encoders": {ObjectId: str},
    }


# Authentication models
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None


class UserInDB(User):
    hashed_password: str


# Query parameters
class QueryParams(BaseModel):
    agent_name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, le=1000)
    skip: int = Field(default=0, ge=0)


# API Key models
class APIKeyCreate(BaseModel):
    name: str = Field(..., description="Friendly name for the API key")
    description: Optional[str] = None
    device_id: Optional[str] = Field(None, description="Device fingerprint (required for non-admin keys)")
    is_admin: bool = Field(default=False, description="Whether this is an admin key")


class APIKeyResponse(BaseModel):
    name: str
    key: str = Field(..., description="The actual API key (only shown once)")
    description: Optional[str] = None
    device_id: Optional[str] = Field(None, description="Device fingerprint this key is tied to")
    is_admin: bool = Field(default=False, description="Whether this is an admin key")
    created_at: datetime


class APIKeyInfo(BaseModel):
    name: str
    description: Optional[str] = None
    device_fingerprint: Optional[str] = Field(None, description="Partial device fingerprint for identification")
    is_admin: bool = Field(default=False, description="Whether this is an admin key")
    created_at: datetime
    last_used: Optional[datetime] = None


# Email Newsletter models
class NewsletterEmailBase(BaseModel):
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$', description="Valid email address")


class NewsletterEmailCreate(NewsletterEmailBase):
    pass


class NewsletterEmailResponse(NewsletterEmailBase):
    id: Optional[str] = Field(alias="_id", default=None)
    subscribed_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "json_encoders": {ObjectId: str},
    }
