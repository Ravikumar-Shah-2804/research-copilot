"""
Authentication schemas
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime


class Token(BaseModel):
    """Token response"""
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None


class TokenData(BaseModel):
    """Token data"""
    username: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


class RevokeTokenRequest(BaseModel):
    """Token revocation request"""
    token: str
    reason: Optional[str] = None


class TokenInfo(BaseModel):
    """Token information"""
    id: UUID
    user_id: UUID
    expires_at: datetime
    revoked_at: Optional[datetime]
    revoked_reason: Optional[str]
    device_info: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    last_used_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """User creation schema"""
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    """User response schema"""
    id: UUID
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    organization_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True