"""
Role and permission management service
"""
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from ..models.role import Role, Permission, Organization, APIKey
from ..models.user import User
from ..schemas.role import (
    RoleCreate, RoleUpdate, PermissionCreate, PermissionUpdate,
    OrganizationCreate, OrganizationUpdate, APIKeyCreate, APIKeyUpdate
)
from ..utils.exceptions import NotFoundError, ValidationError, PermissionDeniedError

logger = logging.getLogger(__name__)


class RoleService:
    """Service for managing roles and permissions"""

    def __init__(self):
        pass

    async def create_permission(
        self, db: AsyncSession, permission_data: PermissionCreate
    ) -> Permission:
        """Create a new permission"""
        # Check if permission already exists
        existing = await db.execute(
            select(Permission).where(
                and_(
                    Permission.resource == permission_data.resource,
                    Permission.action == permission_data.action
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValidationError(f"Permission {permission_data.resource}:{permission_data.action} already exists")

        from datetime import datetime
        permission = Permission(**permission_data.dict())
        # Set timestamps manually for compatibility
        permission.created_at = datetime.now()
        permission.updated_at = datetime.now()
        db.add(permission)
        await db.commit()
        await db.refresh(permission)
        logger.info(f"Created permission: {permission}")
        return permission

    async def get_permission(self, db: AsyncSession, permission_id: UUID) -> Permission:
        """Get permission by ID"""
        result = await db.execute(
            select(Permission).where(Permission.id == permission_id)
        )
        permission = result.scalar_one_or_none()
        if not permission:
            raise NotFoundError(f"Permission {permission_id} not found")
        return permission

    async def update_permission(
        self, db: AsyncSession, permission_id: UUID, update_data: PermissionUpdate
    ) -> Permission:
        """Update permission"""
        permission = await self.get_permission(db, permission_id)

        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(permission, field, value)

        await db.commit()
        await db.refresh(permission)
        logger.info(f"Updated permission: {permission}")
        return permission

    async def delete_permission(self, db: AsyncSession, permission_id: UUID) -> None:
        """Delete permission"""
        permission = await self.get_permission(db, permission_id)
        await db.delete(permission)
        await db.commit()
        logger.info(f"Deleted permission: {permission_id}")

    async def list_permissions(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[Permission]:
        """List all permissions"""
        result = await db.execute(
            select(Permission).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def create_role(self, db: AsyncSession, role_data: RoleCreate) -> Role:
        """Create a new role"""
        # Check if role name already exists (within organization if specified)
        query = select(Role).where(Role.name == role_data.name)
        if role_data.organization_id:
            query = query.where(Role.organization_id == role_data.organization_id)
        else:
            query = query.where(Role.organization_id.is_(None))

        existing = await db.execute(query)
        if existing.scalar_one_or_none():
            org_msg = f" in organization {role_data.organization_id}" if role_data.organization_id else ""
            raise ValidationError(f"Role '{role_data.name}' already exists{org_msg}")

        from datetime import datetime
        role = Role(**role_data.dict(exclude={'permission_ids'}))
        # Set timestamps manually for compatibility
        role.created_at = datetime.now()
        role.updated_at = datetime.now()
        db.add(role)

        # Add permissions if specified
        if role_data.permission_ids:
            permissions = await db.execute(
                select(Permission).where(Permission.id.in_(role_data.permission_ids))
            )
            role.permissions.extend(permissions.scalars().all())

        await db.commit()
        await db.refresh(role)
        logger.info(f"Created role: {role}")
        return role

    async def get_role(self, db: AsyncSession, role_id: UUID) -> Role:
        """Get role by ID with permissions loaded"""
        result = await db.execute(
            select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
        )
        role = result.scalar_one_or_none()
        if not role:
            raise NotFoundError(f"Role {role_id} not found")
        return role

    async def update_role(
        self, db: AsyncSession, role_id: UUID, update_data: RoleUpdate
    ) -> Role:
        """Update role"""
        role = await self.get_role(db, role_id)

        # Prevent updating system roles
        if role.is_system:
            raise PermissionDeniedError("Cannot modify system roles")

        update_dict = update_data.dict(exclude_unset=True, exclude={'permission_ids'})

        # Update basic fields
        for field, value in update_dict.items():
            setattr(role, field, value)

        # Update permissions if specified
        if update_data.permission_ids is not None:
            permissions = await db.execute(
                select(Permission).where(Permission.id.in_(update_data.permission_ids))
            )
            role.permissions = permissions.scalars().all()

        await db.commit()
        await db.refresh(role)
        logger.info(f"Updated role: {role}")
        return role

    async def delete_role(self, db: AsyncSession, role_id: UUID) -> None:
        """Delete role"""
        role = await self.get_role(db, role_id)

        # Prevent deleting system roles
        if role.is_system:
            raise PermissionDeniedError("Cannot delete system roles")

        await db.delete(role)
        await db.commit()
        logger.info(f"Deleted role: {role_id}")

    async def list_roles(
        self, db: AsyncSession, organization_id: Optional[UUID] = None,
        skip: int = 0, limit: int = 100
    ) -> List[Role]:
        """List roles, optionally filtered by organization"""
        query = select(Role).options(selectinload(Role.permissions))
        if organization_id:
            query = query.where(Role.organization_id == organization_id)
        else:
            query = query.where(Role.organization_id.is_(None))

        result = await db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()

    async def assign_role_to_user(
        self, db: AsyncSession, user_id: UUID, role_id: UUID
    ) -> None:
        """Assign role to user"""
        user = await db.get(User, user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        role = await self.get_role(db, role_id)

        # Check organization compatibility
        if user.organization_id != role.organization_id and role.organization_id is not None:
            raise ValidationError("Cannot assign organization-specific role to user from different organization")

        if role not in user.roles:
            user.roles.append(role)
            await db.commit()
            logger.info(f"Assigned role {role_id} to user {user_id}")

    async def remove_role_from_user(
        self, db: AsyncSession, user_id: UUID, role_id: UUID
    ) -> None:
        """Remove role from user"""
        user = await db.get(User, user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        role = await self.get_role(db, role_id)

        if role in user.roles:
            user.roles.remove(role)
            await db.commit()
            logger.info(f"Removed role {role_id} from user {user_id}")

    async def get_user_permissions(self, db: AsyncSession, user_id: UUID) -> List[Permission]:
        """Get all permissions for a user"""
        user = await db.execute(
            select(User).options(
                selectinload(User.roles).selectinload(Role.permissions)
            ).where(User.id == user_id)
        )
        user = user.scalar_one_or_none()
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        permissions = set()
        for role in user.roles:
            permissions.update(role.permissions)

        return list(permissions)

    async def check_user_permission(
        self, db: AsyncSession, user_id: UUID, resource: str, action: str
    ) -> bool:
        """Check if user has specific permission"""
        user = await db.execute(
            select(User).options(
                selectinload(User.roles).selectinload(Role.permissions)
            ).where(User.id == user_id)
        )
        user = user.scalar_one_or_none()
        if not user:
            return False

        # Superusers have all permissions
        if user.is_superuser:
            return True

        for role in user.roles:
            for permission in role.permissions:
                if permission.resource == resource and permission.action == action:
                    return True

        return False


# Global role service instance
role_service = RoleService()