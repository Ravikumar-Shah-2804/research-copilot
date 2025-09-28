"""
Organization management router
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
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    UserRoleAssignment, UserRoleRemoval
)

router = APIRouter()


# Organization CRUD endpoints
@router.post("/", response_model=OrganizationResponse)
async def create_organization(
    org: OrganizationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new organization (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can create organizations"
        )

    try:
        from ..services.organization import organization_service
        return await organization_service.create_organization(db, org)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[OrganizationResponse])
async def list_organizations(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all organizations"""
    try:
        from ..services.organization import organization_service
        return await organization_service.list_organizations(db, skip, limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization by ID"""
    try:
        from ..services.organization import organization_service
        return await organization_service.get_organization(db, org_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: UUID,
    org_update: OrganizationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update organization (admin or org owner only)"""
    try:
        from ..services.organization import organization_service

        # Check permissions
        org = await organization_service.get_organization(db, org_id)
        if not current_user.is_superuser and current_user.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify other organizations"
            )

        return await organization_service.update_organization(db, org_id, org_update)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{org_id}")
async def delete_organization(
    org_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete organization (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can delete organizations"
        )

    try:
        from ..services.organization import organization_service
        await organization_service.delete_organization(db, org_id)
        return {"message": "Organization deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Organization user management
@router.get("/{org_id}/users")
async def get_organization_users(
    org_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get users in organization"""
    try:
        from ..services.organization import organization_service

        # Check permissions
        if not current_user.is_superuser and current_user.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot view other organizations"
            )

        return await organization_service.get_organization_users(db, org_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{org_id}/users/{user_id}")
async def add_user_to_organization(
    org_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Add user to organization (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can manage organization membership"
        )

    try:
        from ..services.organization import organization_service
        await organization_service.add_user_to_organization(db, user_id, org_id)
        return {"message": "User added to organization successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{org_id}/users/{user_id}")
async def remove_user_from_organization(
    org_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove user from organization (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can manage organization membership"
        )

    try:
        from ..services.organization import organization_service
        await organization_service.remove_user_from_organization(db, user_id, org_id)
        return {"message": "User removed from organization successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Organization API key management
@router.get("/{org_id}/api-keys")
async def get_organization_api_keys(
    org_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get API keys for organization"""
    try:
        from ..services.api_key import api_key_service

        # Check permissions
        if not current_user.is_superuser and current_user.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot view other organizations' API keys"
            )

        return await api_key_service.get_organization_api_keys(db, org_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{org_id}/transfer/{user_id}")
async def transfer_user_to_organization(
    org_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Transfer user to different organization (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can transfer users between organizations"
        )

    try:
        from ..services.organization import organization_service
        await organization_service.transfer_user_to_organization(db, user_id, org_id)
        return {"message": "User transferred successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))