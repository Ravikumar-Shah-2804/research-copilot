"""
API Keys management router
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..models.role import APIKey
from ..services.auth import get_current_active_user
from ..services.api_key import api_key_service
from ..services.organization import organization_service
from ..schemas.role import APIKeyCreate, APIKeyUpdate, APIKeyResponse, APIKeyWithSecret

router = APIRouter()


@router.post("/", response_model=APIKeyWithSecret)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new API key"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Creating API key for user {current_user.id}, organization {key_data.organization_id}")

    # Check if user can create API keys for this organization
    if not current_user.is_superuser:
        logger.debug(f"User {current_user.id} is not superuser, checking organization membership")
        # Check if user belongs to the organization
        if current_user.organization_id != key_data.organization_id:
            logger.warning(f"User {current_user.id} organization {current_user.organization_id} != {key_data.organization_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create API keys for other organizations"
            )

        # Check if user has permission to create API keys
        if not current_user.has_permission("api_keys", "write"):
            logger.warning(f"User {current_user.id} lacks api_keys:write permission")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to create API keys"
            )

    try:
        logger.debug(f"Calling api_key_service.create_api_key")
        api_key, plain_key = await api_key_service.create_api_key(
            db, key_data, current_user.id
        )

        logger.info(f"Successfully created API key {api_key.id} for organization {key_data.organization_id}")
        # Return with the plain key (only shown once)
        return APIKeyWithSecret(
            **APIKeyResponse.from_orm(api_key).dict(),
            key=plain_key
        )
    except Exception as e:
        logger.error(f"Failed to create API key: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[APIKeyResponse])
async def list_api_keys(
    organization_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List API keys"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Listing API keys for user {current_user.id}, requested org {organization_id}")

    # Filter by organization if specified
    if organization_id:
        # Check permissions
        if not current_user.is_superuser and current_user.organization_id != organization_id:
            logger.warning(f"User {current_user.id} cannot view API keys for org {organization_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot view API keys for other organizations"
            )
    else:
        # If no organization specified, show user's organization keys
        if not current_user.is_superuser:
            organization_id = current_user.organization_id
            logger.debug(f"Using user's organization {organization_id}")

    try:
        keys = await api_key_service.list_api_keys(
            db, organization_id, None, skip, limit
        )
        logger.info(f"Found {len(keys)} API keys")
        return keys
    except Exception as e:
        logger.error(f"Failed to list API keys: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get API key by ID"""
    try:
        api_key = await api_key_service.get_api_key(db, key_id)

        # Check permissions
        if not current_user.is_superuser and current_user.organization_id != api_key.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot view API keys for other organizations"
            )

        return api_key
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: UUID,
    key_update: APIKeyUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update API key"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Updating API key {key_id} for user {current_user.id}")

    try:
        api_key = await api_key_service.get_api_key(db, key_id)
        logger.debug(f"Found API key {key_id} for org {api_key.organization_id}")

        # Check permissions
        if not current_user.is_superuser and current_user.organization_id != api_key.organization_id:
            logger.warning(f"User {current_user.id} cannot update API key for org {api_key.organization_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update API keys for other organizations"
            )

        updated_key = await api_key_service.update_api_key(db, key_id, key_update)
        logger.info(f"Successfully updated API key {key_id}")
        return updated_key
    except Exception as e:
        logger.error(f"Failed to update API key {key_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete API key"""
    try:
        api_key = await api_key_service.get_api_key(db, key_id)

        # Check permissions
        if not current_user.is_superuser and current_user.organization_id != api_key.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete API keys for other organizations"
            )

        await api_key_service.delete_api_key(db, key_id)
        return {"message": "API key deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{key_id}/revoke")
async def revoke_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Revoke (deactivate) API key"""
    try:
        api_key = await api_key_service.get_api_key(db, key_id)

        # Check permissions
        if not current_user.is_superuser and current_user.organization_id != api_key.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot revoke API keys for other organizations"
            )

        await api_key_service.revoke_api_key(db, key_id)
        return {"message": "API key revoked successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{key_id}/rotate", response_model=APIKeyWithSecret)
async def rotate_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Rotate API key (generate new key)"""
    try:
        api_key = await api_key_service.get_api_key(db, key_id)

        # Check permissions
        if not current_user.is_superuser and current_user.organization_id != api_key.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot rotate API keys for other organizations"
            )

        rotated_key, plain_key = await api_key_service.rotate_api_key(db, key_id)

        # Return with the new plain key
        return APIKeyWithSecret(
            **APIKeyResponse.from_orm(rotated_key).dict(),
            key=plain_key
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats/summary")
async def get_api_key_stats(
    organization_id: UUID = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get API key statistics"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Getting API key stats for user {current_user.id}, requested org {organization_id}")

    # Check permissions for organization-specific stats
    if organization_id and not current_user.is_superuser and current_user.organization_id != organization_id:
        logger.warning(f"User {current_user.id} cannot view stats for org {organization_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view statistics for other organizations"
        )

    # If no organization specified and not superuser, use user's organization
    if not organization_id and not current_user.is_superuser:
        organization_id = current_user.organization_id
        logger.debug(f"Using user's organization {organization_id}")

    try:
        stats = await api_key_service.get_api_key_stats(db, organization_id)
        logger.info(f"Retrieved stats: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Failed to get API key stats: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))