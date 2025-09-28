"""
Refresh token service for JWT token management
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func

from ..models.refresh_token import RefreshToken
from ..models.user import User
from ..config import settings
from ..utils.exceptions import NotFoundError, ValidationError, AuthenticationError

import logging
logger = logging.getLogger(__name__)


class RefreshTokenService:
    """Service for managing refresh tokens"""

    def __init__(self):
        pass

    def _hash_token(self, token: str) -> str:
        """Hash refresh token for storage"""
        return hashlib.sha256(token.encode()).hexdigest()

    def _generate_refresh_token(self) -> str:
        """Generate a new refresh token"""
        return secrets.token_urlsafe(64)

    async def create_refresh_token(
        self,
        db: AsyncSession,
        user_id: UUID,
        expires_days: int = None,
        device_info: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> tuple[RefreshToken, str]:
        """Create a new refresh token and return both the model and the plain token"""
        if expires_days is None:
            expires_days = settings.jwt_refresh_token_expire_days

        plain_token = self._generate_refresh_token()
        token_hash = self._hash_token(plain_token)

        expires_at = datetime.utcnow() + timedelta(days=expires_days)

        refresh_token = RefreshToken(
            token_hash=token_hash,
            user_id=user_id,
            expires_at=expires_at,
            device_info=device_info,
            ip_address=ip_address,
            user_agent=user_agent
        )

        db.add(refresh_token)
        await db.commit()
        await db.refresh(refresh_token)

        logger.info(f"Created refresh token for user {user_id}")
        return refresh_token, plain_token

    async def validate_refresh_token(self, db: AsyncSession, token: str) -> RefreshToken:
        """Validate a refresh token and return the token record"""
        token_hash = self._hash_token(token)

        result = await db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.token_hash == token_hash,
                    RefreshToken.revoked_at.is_(None),
                    RefreshToken.expires_at > datetime.utcnow()
                )
            )
        )

        refresh_token = result.scalar_one_or_none()
        if not refresh_token:
            raise AuthenticationError("Invalid or expired refresh token")

        # Update last used timestamp
        await db.execute(
            update(RefreshToken).where(RefreshToken.id == refresh_token.id).values(
                last_used_at=datetime.utcnow()
            )
        )
        await db.commit()

        return refresh_token

    async def revoke_refresh_token(
        self, db: AsyncSession, token: str, reason: str = None
    ) -> None:
        """Revoke a refresh token"""
        token_hash = self._hash_token(token)

        result = await db.execute(
            update(RefreshToken).where(
                and_(
                    RefreshToken.token_hash == token_hash,
                    RefreshToken.revoked_at.is_(None)
                )
            ).values(
                revoked_at=datetime.utcnow(),
                revoked_reason=reason
            )
        )

        if result.rowcount == 0:
            raise NotFoundError("Refresh token not found or already revoked")

        await db.commit()
        logger.info(f"Revoked refresh token: {reason or 'No reason provided'}")

    async def revoke_all_user_tokens(
        self, db: AsyncSession, user_id: UUID, reason: str = "User logout"
    ) -> int:
        """Revoke all refresh tokens for a user"""
        result = await db.execute(
            update(RefreshToken).where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked_at.is_(None)
                )
            ).values(
                revoked_at=datetime.utcnow(),
                revoked_reason=reason
            )
        )

        await db.commit()
        revoked_count = result.rowcount
        logger.info(f"Revoked {revoked_count} refresh tokens for user {user_id}")
        return revoked_count

    async def get_user_tokens(
        self, db: AsyncSession, user_id: UUID, include_revoked: bool = False
    ) -> List[RefreshToken]:
        """Get all refresh tokens for a user"""
        query = select(RefreshToken).where(RefreshToken.user_id == user_id)

        if not include_revoked:
            query = query.where(RefreshToken.revoked_at.is_(None))

        result = await db.execute(query.order_by(RefreshToken.created_at.desc()))
        return result.scalars().all()

    async def cleanup_expired_tokens(self, db: AsyncSession) -> int:
        """Clean up expired refresh tokens"""
        result = await db.execute(
            delete(RefreshToken).where(
                or_(
                    RefreshToken.expires_at <= datetime.utcnow(),
                    and_(
                        RefreshToken.revoked_at.is_not(None),
                        RefreshToken.revoked_at <= datetime.utcnow() - timedelta(days=30)  # Keep revoked tokens for 30 days
                    )
                )
            )
        )

        deleted_count = result.rowcount
        await db.commit()

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired/revoked refresh tokens")

        return deleted_count

    async def get_token_info(self, db: AsyncSession, token: str) -> RefreshToken:
        """Get information about a refresh token (without validating it)"""
        token_hash = self._hash_token(token)

        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )

        refresh_token = result.scalar_one_or_none()
        if not refresh_token:
            raise NotFoundError("Refresh token not found")

        return refresh_token

    async def get_token_stats(self, db: AsyncSession, user_id: Optional[UUID] = None) -> dict:
        """Get refresh token statistics"""
        base_query = select(
            func.count(RefreshToken.id).label('total_tokens'),
            func.count(RefreshToken.id).filter(RefreshToken.revoked_at.is_(None)).label('active_tokens'),
            func.count(RefreshToken.id).filter(RefreshToken.revoked_at.is_not(None)).label('revoked_tokens'),
            func.count(RefreshToken.id).filter(
                and_(
                    RefreshToken.expires_at > datetime.utcnow(),
                    RefreshToken.revoked_at.is_(None)
                )
            ).label('valid_tokens')
        )

        if user_id:
            base_query = base_query.where(RefreshToken.user_id == user_id)

        result = await db.execute(base_query)
        row = result.first()

        return {
            "total_tokens": row.total_tokens or 0,
            "active_tokens": row.active_tokens or 0,
            "revoked_tokens": row.revoked_tokens or 0,
            "valid_tokens": row.valid_tokens or 0,
            "user_id": str(user_id) if user_id else None
        }


# Global refresh token service instance
refresh_token_service = RefreshTokenService()