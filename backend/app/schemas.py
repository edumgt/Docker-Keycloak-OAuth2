from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


MemberStage = Literal[
    "visitor",
    "consulting_customer",
    "member",
    "service_user",
    "medical_service_user",
]
AccountStatus = Literal["active", "dormant", "withdrawn"]
ConsentType = Literal["common", "service"]


class MemberCreate(BaseModel):
    customer_id: str = Field(min_length=3, max_length=36)
    email: EmailStr
    stage: MemberStage = "visitor"
    account_status: AccountStatus = "active"


class MemberStatusUpdate(BaseModel):
    account_status: AccountStatus


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: str
    email: EmailStr
    stage: MemberStage
    account_status: AccountStatus
    created_at: datetime
    updated_at: datetime


class ConsentCreate(BaseModel):
    customer_id: str
    consent_type: ConsentType = "common"
    service_name: str | None = None
    purpose: str = Field(min_length=2, max_length=120)
    is_required: bool = True
    is_agreed: bool = False
    consent_version: str = Field(min_length=1, max_length=40)
    country_code: str = Field(min_length=2, max_length=5, default="KR")
    language_code: str = Field(min_length=2, max_length=10, default="ko")


class ConsentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    consent_type: ConsentType
    service_name: str | None
    purpose: str
    is_required: bool
    is_agreed: bool
    consent_version: str
    country_code: str
    language_code: str
    created_at: datetime


class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    expires_in: int | None = None
    refresh_expires_in: int | None = None
    refresh_token: str | None = None
    token_type: str | None = None
    not_before_policy: int | None = None
    session_state: str | None = None
    scope: str | None = None


class HealthResponse(BaseModel):
    status: str
    database: str
    keycloak: str


class UserInfoResponse(BaseModel):
    payload: dict[str, Any]
