"""
User model
"""
from sqlalchemy import Boolean, Column, String, DateTime, func, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from ..database import Base

if TYPE_CHECKING:
    from .role import Organization


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="users")
    roles = relationship("Role", secondary="user_roles", back_populates="users")
    created_api_keys = relationship("APIKey", foreign_keys="APIKey.created_by", back_populates="creator")

    def has_permission(self, resource: str, action: str) -> bool:
        """Check if user has a specific permission"""
        if self.is_superuser:
            return True

        for role in self.roles:
            for permission in role.permissions:
                if permission.resource == resource and permission.action == action:
                    return True
        return False

    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role"""
        return any(role.name == role_name for role in self.roles)

    def is_account_locked(self) -> bool:
        """Check if account is currently locked"""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False