"""
API Key authentication and management service
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_

from ..models.role import APIKey
from ..models.user import User
from ..schemas.role import APIKeyCreate, APIKeyUpdate, APIKeyResponse
from ..utils.exceptions import NotFoundError, ValidationError, AuthenticationError

import logging
logger = logging.getLogger(__name__)


class APIKeyService:
    """Service for managing API keys"""

    def __init__(self):
        pass

    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def _generate_api_key(self) -> str:
        """Generate a new API key"""
        return f"rc_{secrets.token_urlsafe(32)}"

    async def create_api_key(
        self, db: AsyncSession, key_data: APIKeyCreate, created_by: UUID
    ) -> tuple[APIKey, str]:
        """Create a new API key and return both the model and the plain key"""
        # Generate the actual key
        plain_key = self._generate_api_key()
        key_hash = self._hash_api_key(plain_key)

        # Check if name already exists for this organization
        existing = await db.execute(
            select(APIKey).where(
                and_(
                    APIKey.organization_id == key_data.organization_id,
                    APIKey.name == key_data.name
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValidationError(f"API key with name '{key_data.name}' already exists in this organization")

        # Create API key record
        api_key = APIKey(
            key_hash=key_hash,
            name=key_data.name,
            description=key_data.description,
            organization_id=key_data.organization_id,
            created_by=created_by,
            expires_at=key_data.expires_at,
            permissions=key_data.permissions,
            rate_limit=key_data.rate_limit
        )

        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)

        logger.info(f"Created API key: {api_key.name} for organization {key_data.organization_id}")
        return api_key, plain_key

    async def authenticate_api_key(self, db: AsyncSession, api_key: str) -> APIKey:
        """Authenticate an API key and return the key record"""
        key_hash = self._hash_api_key(api_key)

        result = await db.execute(
            select(APIKey).where(
                and_(
                    APIKey.key_hash == key_hash,
                    APIKey.is_active == True,
                    or_(
                        APIKey.expires_at.is_(None),
                        APIKey.expires_at > datetime.utcnow()
                    )
                )
            )
        )

        api_key_record = result.scalar_one_or_none()
        if not api_key_record:
            raise AuthenticationError("Invalid or expired API key")

        # Update last used timestamp
        await db.execute(
            update(APIKey).where(APIKey.id == api_key_record.id).values(
                last_used_at=datetime.utcnow()
            )
        )
        await db.commit()

        return api_key_record

    async def get_api_key(self, db: AsyncSession, key_id: UUID) -> APIKey:
        """Get API key by ID"""
        result = await db.execute(select(APIKey).where(APIKey.id == key_id))
        api_key = result.scalar_one_or_none()
        if not api_key:
            raise NotFoundError(f"API key {key_id} not found")
        return api_key

    async def update_api_key(
        self, db: AsyncSession, key_id: UUID, update_data: APIKeyUpdate
    ) -> APIKey:
        """Update API key"""
        api_key = await self.get_api_key(db, key_id)

        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(api_key, field, value)

        await db.commit()
        await db.refresh(api_key)
        logger.info(f"Updated API key: {api_key.name}")
        return api_key

    async def delete_api_key(self, db: AsyncSession, key_id: UUID) -> None:
        """Delete API key"""
        api_key = await self.get_api_key(db, key_id)
        await db.delete(api_key)
        await db.commit()
        logger.info(f"Deleted API key: {api_key.name}")

    async def list_api_keys(
        self, db: AsyncSession, organization_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None, skip: int = 0, limit: int = 100
    ) -> List[APIKey]:
        """List API keys with optional filters"""
        query = select(APIKey)

        if organization_id:
            query = query.where(APIKey.organization_id == organization_id)
        if created_by:
            query = query.where(APIKey.created_by == created_by)

        result = await db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()

    async def revoke_api_key(self, db: AsyncSession, key_id: UUID) -> None:
        """Revoke (deactivate) an API key"""
        api_key = await self.get_api_key(db, key_id)
        api_key.is_active = False
        await db.commit()
        logger.info(f"Revoked API key: {api_key.name}")

    async def check_api_key_permission(self, api_key: APIKey, resource: str, action: str) -> bool:
        """Check if API key has permission for a resource/action"""
        if not api_key.permissions:
            return False

        required_permission = f"{resource}:{action}"
        return required_permission in api_key.permissions

    async def get_api_key_stats(self, db: AsyncSession, organization_id: Optional[UUID] = None) -> dict:
        """Get API key statistics"""
        from sqlalchemy import func

        query = select(
            func.count(APIKey.id).label('total_keys'),
            func.count(APIKey.id).filter(APIKey.is_active == True).label('active_keys'),
            func.count(APIKey.id).filter(APIKey.is_active == False).label('revoked_keys'),
            func.avg(APIKey.rate_limit).label('avg_rate_limit')
        )

        if organization_id:
            query = query.where(APIKey.organization_id == organization_id)

        result = await db.execute(query)
        row = result.first()

        return {
            "total_keys": row.total_keys or 0,
            "active_keys": row.active_keys or 0,
            "revoked_keys": row.revoked_keys or 0,
            "avg_rate_limit": float(row.avg_rate_limit) if row.avg_rate_limit else 0.0
        }

    async def rotate_api_key(self, db: AsyncSession, key_id: UUID) -> tuple[APIKey, str]:
        """Rotate an API key (generate new key, keep same settings)"""
        api_key = await self.get_api_key(db, key_id)

        # Generate new key
        plain_key = self._generate_api_key()
        key_hash = self._hash_api_key(plain_key)

        # Update the key hash
        api_key.key_hash = key_hash
        api_key.last_used_at = None  # Reset last used timestamp

        await db.commit()
        await db.refresh(api_key)

        logger.info(f"Rotated API key: {api_key.name}")
        return api_key, plain_key


# Global API key service instance
api_key_service = APIKeyService()