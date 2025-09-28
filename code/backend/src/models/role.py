"""
Role and permission models for RBAC
"""
from sqlalchemy import Boolean, Column, String, Text, DateTime, ForeignKey, Table, Integer
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSON
from sqlalchemy.orm import relationship
import uuid
from typing import List, TYPE_CHECKING

from ..database import Base

if TYPE_CHECKING:
    from .user import User


# Association table for user-role many-to-many relationship
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True)
)

# Association table for role-permission many-to-many relationship
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('permissions.id'), primary_key=True)
)


class Permission(Base):
    """Permission model for fine-grained access control"""
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    resource = Column(String(100), nullable=False)  # e.g., 'papers', 'users', 'analytics'
    action = Column(String(50), nullable=False)     # e.g., 'read', 'write', 'delete', 'admin'
    created_at = Column(DateTime(timezone=True), server_default='now()')
    updated_at = Column(DateTime(timezone=True), server_default='now()', onupdate='now()')

    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

    def __str__(self):
        return f"{self.resource}:{self.action}"


class Role(Base):
    """Role model for RBAC"""
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    is_default = Column(Boolean, default=False)  # Default role for new users
    is_system = Column(Boolean, default=False)  # System roles that cannot be deleted
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default='now()')
    updated_at = Column(DateTime(timezone=True), server_default='now()', onupdate='now()')

    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    organization = relationship("Organization", back_populates="roles")

    def __str__(self):
        return self.name


class Organization(Base):
    """Organization model for multi-tenancy"""
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    domain = Column(String(255), unique=True, nullable=True)  # For domain-based tenant isolation
    is_active = Column(Boolean, default=True)
    max_users = Column(Integer, default=100)
    subscription_tier = Column(String(50), default='free')  # free, basic, premium, enterprise
    settings = Column(JSON, default=dict)  # Flexible settings storage
    created_at = Column(DateTime(timezone=True), server_default='now()')
    updated_at = Column(DateTime(timezone=True), server_default='now()', onupdate='now()')

    # Relationships
    users = relationship("User", back_populates="organization")
    roles = relationship("Role", back_populates="organization")
    api_keys = relationship("APIKey", back_populates="organization")

    def __str__(self):
        return self.name


class APIKey(Base):
    """API Key model for service-to-service authentication"""
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    permissions = Column(ARRAY(String), default=list)  # List of allowed permissions
    rate_limit = Column(Integer, default=1000)  # Requests per hour
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default='now()')
    updated_at = Column(DateTime(timezone=True), server_default='now()', onupdate='now()')

    # Relationships
    organization = relationship("Organization", back_populates="api_keys")
    creator = relationship("User")

    def __str__(self):
        return f"{self.name} ({self.organization.name})"