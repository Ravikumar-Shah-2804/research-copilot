"""
Organization isolation middleware for multi-tenancy
"""
import logging
from typing import Callable
from fastapi import Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.organization import organization_service

logger = logging.getLogger(__name__)


class OrganizationIsolationMiddleware:
    """Middleware to enforce organization isolation"""

    def __init__(self, app: Callable):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract request information
        request = Request(scope, receive)

        # Get database session from request state (injected by FastAPI)
        # This is a bit of a hack, but necessary for middleware
        db = None
        try:
            # Try to get from request state if available
            db = getattr(request.state, 'db', None)
        except:
            pass

        if not db:
            # Fallback: create a new session (not ideal but works)
            from ..database import async_session
            async with async_session() as session:
                db = session
                await self._process_request_with_db(request, db)
        else:
            await self._process_request_with_db(request, db)

        await self.app(scope, receive, send)

    async def _process_request_with_db(self, request: Request, db: AsyncSession):
        """Process request with database context"""
        # Extract organization from various sources
        organization_id = await self._extract_organization(request, db)

        # Set organization context in request state
        request.state.organization_id = organization_id

        # Log organization context
        if organization_id:
            logger.debug(f"Request organization context: {organization_id}")
        else:
            logger.debug("Request has no organization context")

    async def _extract_organization(self, request: Request, db: AsyncSession) -> str:
        """Extract organization ID from request"""
        # Method 1: From user authentication (if available)
        try:
            user = getattr(request.state, 'user', None)
            if user and hasattr(user, 'organization_id') and user.organization_id:
                return str(user.organization_id)
        except:
            pass

        # Method 2: From domain-based routing
        host = request.headers.get('host', '').lower()
        if host:
            # Remove port if present
            domain = host.split(':')[0]

            # Check if domain matches an organization
            org = await organization_service.get_organization_by_domain(db, domain)
            if org:
                return str(org.id)

        # Method 3: From API key (if available)
        api_key = getattr(request.state, 'api_key', None)
        if api_key and hasattr(api_key, 'organization_id'):
            return str(api_key.organization_id)

        # Method 4: From query parameter or header (for service-to-service calls)
        org_id = request.query_params.get('organization_id') or request.headers.get('X-Organization-ID')
        if org_id:
            # Validate that organization exists
            try:
                from uuid import UUID
                org_uuid = UUID(org_id)
                org = await organization_service.get_organization(db, org_uuid)
                return str(org.id)
            except:
                pass

        return None


def get_current_organization_id(request: Request) -> str:
    """Get current organization ID from request context"""
    return getattr(request.state, 'organization_id', None)


def require_organization_access(organization_id: str = None):
    """Dependency to require organization access"""
    def dependency(request: Request):
        current_org_id = get_current_organization_id(request)

        if not current_org_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No organization context available"
            )

        if organization_id and current_org_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: organization mismatch"
            )

        return current_org_id

    return dependency


def require_organization_membership():
    """Dependency to require user belongs to the current organization"""
    def dependency(request: Request):
        current_org_id = get_current_organization_id(request)
        user = getattr(request.state, 'user', None)

        if not current_org_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No organization context available"
            )

        if not user or not hasattr(user, 'organization_id'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        if str(user.organization_id) != current_org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: not a member of this organization"
            )

        return current_org_id

    return dependency