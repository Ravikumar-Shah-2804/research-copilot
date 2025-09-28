"""
API Key authentication middleware
"""
import logging
from typing import Callable, Optional
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.api_key import api_key_service
from ..models.role import APIKey

logger = logging.getLogger(__name__)

# API key header name
API_KEY_HEADER = "X-API-Key"


class APIKeyAuthMiddleware:
    """Middleware for API key authentication"""

    def __init__(self, app: Callable):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Extract API key from header
        api_key = request.headers.get(API_KEY_HEADER)

        if api_key:
            # Get database session
            db = None
            try:
                # Try to get from request state
                db = getattr(request.state, 'db', None)
            except:
                pass

            if not db:
                # Fallback: create new session
                from ..database import async_session
                async with async_session() as session:
                    db = session
                    await self._authenticate_api_key(request, api_key, db)
            else:
                await self._authenticate_api_key(request, api_key, db)

        await self.app(scope, receive, send)

    async def _authenticate_api_key(self, request: Request, api_key: str, db: AsyncSession):
        """Authenticate API key and set in request state"""
        try:
            api_key_record = await api_key_service.authenticate_api_key(db, api_key)
            request.state.api_key = api_key_record
            request.state.organization_id = str(api_key_record.organization_id)
            logger.debug(f"API key authenticated: {api_key_record.name}")
        except Exception as e:
            # Don't fail here - let individual endpoints decide if API key is required
            logger.debug(f"API key authentication failed: {e}")


# FastAPI security scheme for API key
api_key_scheme = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


async def get_current_api_key(
    api_key: Optional[str] = Depends(api_key_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[APIKey]:
    """Get current API key from request"""
    if not api_key:
        return None

    try:
        return await api_key_service.authenticate_api_key(db, api_key)
    except Exception:
        return None


def require_api_key():
    """Dependency to require API key authentication"""
    async def dependency(
        api_key: Optional[str] = Depends(api_key_scheme),
        db: AsyncSession = Depends(get_db)
    ) -> APIKey:
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        try:
            return await api_key_service.authenticate_api_key(db, api_key)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )

    return dependency


def require_api_key_permission(resource: str, action: str):
    """Dependency to require specific API key permission"""
    async def dependency(api_key: APIKey = Depends(require_api_key())) -> APIKey:
        has_permission = await api_key_service.check_api_key_permission(
            api_key, resource, action
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key does not have permission for {resource}:{action}"
            )

        return api_key

    return dependency


def optional_api_key():
    """Optional API key dependency"""
    return get_current_api_key