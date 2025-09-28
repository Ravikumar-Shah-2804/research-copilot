"""
Pydantic schemas for roles, permissions, organizations, and API keys
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, validator


class PermissionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    resource: str = Field(..., min_length=1, max_length=100)
    action: str = Field(..., min_length=1, max_length=50)


class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    resource: Optional[str] = Field(None, min_length=1, max_length=100)
    action: Optional[str] = Field(None, min_length=1, max_length=50)


class PermissionResponse(PermissionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    is_default: bool = False
    organization_id: Optional[UUID] = None


class RoleCreate(RoleBase):
    permission_ids: List[UUID] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_default: Optional[bool] = None
    permission_ids: Optional[List[UUID]] = None


class RoleResponse(RoleBase):
    id: UUID
    is_system: bool
    permissions: List[PermissionResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    domain: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    max_users: int = Field(default=100, ge=1)
    subscription_tier: str = Field(default="free", pattern=r'^(free|basic|premium|enterprise)$')


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    domain: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    max_users: Optional[int] = Field(None, ge=1)
    subscription_tier: Optional[str] = Field(None, pattern=r'^(free|basic|premium|enterprise)$')
    settings: Optional[Dict[str, Any]] = None


class OrganizationResponse(OrganizationBase):
    id: UUID
    is_active: bool
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class APIKeyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    expires_at: Optional[datetime] = None
    permissions: List[str] = Field(default_factory=list)
    rate_limit: int = Field(default=1000, ge=1, le=100000)


class APIKeyCreate(APIKeyBase):
    organization_id: UUID


class APIKeyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    permissions: Optional[List[str]] = None
    rate_limit: Optional[int] = Field(None, ge=1, le=100000)


class APIKeyResponse(APIKeyBase):
    id: UUID
    organization_id: UUID
    created_by: UUID
    is_active: bool
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class APIKeyWithSecret(APIKeyResponse):
    """API Key response that includes the actual key (only shown once during creation)"""
    key: str


# User role assignment schemas
class UserRoleAssignment(BaseModel):
    user_id: UUID
    role_id: UUID


class UserRoleRemoval(BaseModel):
    user_id: UUID
    role_id: UUID


# Permission check schemas
class PermissionCheck(BaseModel):
    resource: str
    action: str


class PermissionCheckResponse(BaseModel):
    has_permission: bool
    user_id: UUID
    resource: str
    action: str
    roles: List[str] = Field(default_factory=list)