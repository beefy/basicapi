from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List, Annotated
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type, _handler
    ):
        from pydantic_core import core_schema
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.str_schema(),
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError("Invalid ObjectId")

    def __str__(self):
        return str(self)


class StatusUpdateBase(BaseModel):
    agent_name: str
    update_text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StatusUpdateCreate(StatusUpdateBase):
    pass


class StatusUpdateResponse(StatusUpdateBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)

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
    id: Optional[PyObjectId] = Field(alias="_id", default=None)

    model_config = {
        "populate_by_name": True,
        "json_encoders": {ObjectId: str},
    }


class ResponseTimeStats(BaseModel):
    agent_name: str
    average_response_time_ms: float
    count: int


class SystemInfoBase(BaseModel):
    agent_name: str
    cpu: float = Field(..., description="CPU usage percentage")
    memory: float = Field(..., description="Memory usage percentage")
    disk: float = Field(..., description="Disk usage percentage")
    ts: datetime = Field(default_factory=datetime.utcnow)


class SystemInfoCreate(SystemInfoBase):
    pass


class SystemInfoResponse(SystemInfoBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)

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
    id: Optional[PyObjectId] = Field(alias="_id", default=None)

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
