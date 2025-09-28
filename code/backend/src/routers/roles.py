"""
Roles and permissions management router
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..services.auth import get_current_active_user
from ..services.role import role_service
from ..schemas.role import (
    PermissionCreate, PermissionUpdate, PermissionResponse,
    RoleCreate, RoleUpdate, RoleResponse,
    UserRoleAssignment, UserRoleRemoval, PermissionCheck, PermissionCheckResponse
)

router = APIRouter()


# Permission endpoints
@router.post("/permissions", response_model=PermissionResponse)
async def create_permission(
    permission: PermissionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new permission (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can create permissions"
        )

    try:
        return await role_service.create_permission(db, permission)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all permissions"""
    return await role_service.list_permissions(db, skip, limit)


@router.get("/permissions/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get permission by ID"""
    try:
        return await role_service.get_permission(db, permission_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/permissions/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    permission_id: UUID,
    permission_update: PermissionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update permission (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can update permissions"
        )

    try:
        return await role_service.update_permission(db, permission_id, permission_update)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/permissions/{permission_id}")
async def delete_permission(
    permission_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete permission (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can delete permissions"
        )

    try:
        await role_service.delete_permission(db, permission_id)
        return {"message": "Permission deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Role endpoints
@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role: RoleCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new role (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can create roles"
        )

    try:
        return await role_service.create_role(db, role)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    organization_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List roles, optionally filtered by organization"""
    return await role_service.list_roles(db, organization_id, skip, limit)


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get role by ID"""
    try:
        return await role_service.get_role(db, role_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    role_update: RoleUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update role (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can update roles"
        )

    try:
        return await role_service.update_role(db, role_id, role_update)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete role (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can delete roles"
        )

    try:
        await role_service.delete_role(db, role_id)
        return {"message": "Role deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# User role assignment endpoints
@router.post("/users/assign-role")
async def assign_role_to_user(
    assignment: UserRoleAssignment,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Assign role to user (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can assign roles"
        )

    try:
        await role_service.assign_role_to_user(db, assignment.user_id, assignment.role_id)
        return {"message": "Role assigned successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/remove-role")
async def remove_role_from_user(
    removal: UserRoleRemoval,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove role from user (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can remove roles"
        )

    try:
        await role_service.remove_role_from_user(db, removal.user_id, removal.role_id)
        return {"message": "Role removed successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users/{user_id}/permissions", response_model=List[PermissionResponse])
async def get_user_permissions(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get permissions for a user"""
    # Users can view their own permissions, admins can view anyone's
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view other users' permissions"
        )

    try:
        return await role_service.get_user_permissions(db, user_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/check-permission", response_model=PermissionCheckResponse)
async def check_user_permission(
    check: PermissionCheck,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Check if current user has specific permission"""
    has_permission = await role_service.check_user_permission(
        db, current_user.id, check.resource, check.action
    )

    return PermissionCheckResponse(
        has_permission=has_permission,
        user_id=current_user.id,
        resource=check.resource,
        action=check.action,
        roles=[role.name for role in current_user.roles]
    )