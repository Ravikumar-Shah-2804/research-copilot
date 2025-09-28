"""
Refresh token model for JWT token management
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from ..database import Base


class RefreshToken(Base):
    """Refresh token model for JWT token blacklisting and management"""
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_reason = Column(String(255))
    device_info = Column(String(500))  # Store device/browser info for security
    ip_address = Column(String(45))    # IPv4/IPv6 address
    user_agent = Column(String(500))   # User agent string
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.utcnow() > self.expires_at.replace(tzinfo=None)

    def is_revoked(self) -> bool:
        """Check if token is revoked"""
        return self.revoked_at is not None

    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not revoked)"""
        return not self.is_expired() and not self.is_revoked()