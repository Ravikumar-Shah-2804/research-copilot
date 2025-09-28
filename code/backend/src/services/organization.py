"""
Organization management service
"""
import logging
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func

from ..models.role import Organization
from ..models.user import User
from ..schemas.role import OrganizationCreate, OrganizationUpdate, OrganizationResponse
from ..utils.exceptions import NotFoundError, ValidationError, PermissionDeniedError

logger = logging.getLogger(__name__)


class OrganizationService:
    """Service for managing organizations"""

    def __init__(self):
        pass

    async def create_organization(
        self, db: AsyncSession, org_data: OrganizationCreate
    ) -> Organization:
        """Create a new organization"""
        # Check if organization name already exists
        existing = await db.execute(
            select(Organization).where(Organization.name == org_data.name)
        )
        if existing.scalar_one_or_none():
            raise ValidationError(f"Organization '{org_data.name}' already exists")

        # Check if domain already exists
        if org_data.domain:
            existing_domain = await db.execute(
                select(Organization).where(Organization.domain == org_data.domain)
            )
            if existing_domain.scalar_one_or_none():
                raise ValidationError(f"Domain '{org_data.domain}' already exists")

        org = Organization(**org_data.dict())
        db.add(org)
        await db.commit()
        await db.refresh(org)
        logger.info(f"Created organization: {org}")
        return org

    async def get_organization(self, db: AsyncSession, org_id: UUID) -> Organization:
        """Get organization by ID"""
        result = await db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = result.scalar_one_or_none()
        if not org:
            raise NotFoundError(f"Organization {org_id} not found")
        return org

    async def update_organization(
        self, db: AsyncSession, org_id: UUID, update_data: OrganizationUpdate
    ) -> Organization:
        """Update organization"""
        org = await self.get_organization(db, org_id)

        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(org, field, value)

        await db.commit()
        await db.refresh(org)
        logger.info(f"Updated organization: {org}")
        return org

    async def delete_organization(self, db: AsyncSession, org_id: UUID) -> None:
        """Delete organization"""
        org = await self.get_organization(db, org_id)

        # Check if organization has users
        user_count = await db.execute(
            select(func.count(User.id)).where(User.organization_id == org_id)
        )
        if user_count.scalar() > 0:
            raise ValidationError("Cannot delete organization with active users")

        await db.delete(org)
        await db.commit()
        logger.info(f"Deleted organization: {org_id}")

    async def list_organizations(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[Organization]:
        """List all organizations"""
        result = await db.execute(
            select(Organization).offset(skip).limit(limit).order_by(Organization.name)
        )
        return result.scalars().all()

    async def get_organization_users(self, db: AsyncSession, org_id: UUID) -> List[User]:
        """Get all users in an organization"""
        await self.get_organization(db, org_id)  # Validate org exists

        result = await db.execute(
            select(User).where(User.organization_id == org_id).order_by(User.username)
        )
        return result.scalars().all()

    async def add_user_to_organization(
        self, db: AsyncSession, user_id: UUID, org_id: UUID
    ) -> None:
        """Add user to organization"""
        user = await db.get(User, user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        org = await self.get_organization(db, org_id)

        # Check user limit
        user_count = await db.execute(
            select(func.count(User.id)).where(User.organization_id == org_id)
        )
        if user_count.scalar() >= org.max_users:
            raise ValidationError(f"Organization has reached maximum user limit ({org.max_users})")

        user.organization_id = org_id
        await db.commit()
        logger.info(f"Added user {user_id} to organization {org_id}")

    async def remove_user_from_organization(
        self, db: AsyncSession, user_id: UUID, org_id: UUID
    ) -> None:
        """Remove user from organization"""
        user = await db.get(User, user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        if user.organization_id != org_id:
            raise ValidationError(f"User {user_id} is not in organization {org_id}")

        user.organization_id = None
        await db.commit()
        logger.info(f"Removed user {user_id} from organization {org_id}")

    async def transfer_user_to_organization(
        self, db: AsyncSession, user_id: UUID, new_org_id: UUID
    ) -> None:
        """Transfer user to different organization"""
        user = await db.get(User, user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        new_org = await self.get_organization(db, new_org_id)

        # Check user limit for new organization
        user_count = await db.execute(
            select(func.count(User.id)).where(User.organization_id == new_org_id)
        )
        if user_count.scalar() >= new_org.max_users:
            raise ValidationError(f"Target organization has reached maximum user limit ({new_org.max_users})")

        old_org_id = user.organization_id
        user.organization_id = new_org_id
        await db.commit()
        logger.info(f"Transferred user {user_id} from organization {old_org_id} to {new_org_id}")

    async def get_organization_stats(self, db: AsyncSession, org_id: UUID) -> dict:
        """Get organization statistics"""
        await self.get_organization(db, org_id)  # Validate org exists

        # Count users
        user_count = await db.execute(
            select(func.count(User.id)).where(User.organization_id == org_id)
        )

        # Count active users
        active_user_count = await db.execute(
            select(func.count(User.id)).where(
                and_(User.organization_id == org_id, User.is_active == True)
            )
        )

        # Count API keys
        from ..models.role import APIKey
        api_key_count = await db.execute(
            select(func.count(APIKey.id)).where(APIKey.organization_id == org_id)
        )

        return {
            "organization_id": str(org_id),
            "total_users": user_count.scalar(),
            "active_users": active_user_count.scalar(),
            "api_keys": api_key_count.scalar()
        }


# Global organization service instance
organization_service = OrganizationService()