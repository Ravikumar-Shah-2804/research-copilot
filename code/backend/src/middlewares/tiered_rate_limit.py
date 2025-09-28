"""
Tiered rate limiting middleware based on user roles and organization tiers
"""
import logging
from typing import Callable
from fastapi import Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.rate_limiting import SearchRateLimiter, RAGRateLimiter

logger = logging.getLogger(__name__)


class TieredRateLimitMiddleware:
    """Middleware for tiered rate limiting based on user roles and organization"""

    def __init__(self, app: Callable):
        self.app = app
        self.search_limiter = SearchRateLimiter()
        self.rag_limiter = RAGRateLimiter()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Get user and organization from request state
        user = getattr(request.state, 'user', None)
        organization = getattr(request.state, 'organization_obj', None)  # Full org object
        api_key = getattr(request.state, 'api_key', None)

        # Determine rate limit based on endpoint
        path = request.url.path
        method = request.method

        try:
            # Apply rate limiting based on endpoint type
            await self._apply_rate_limit(request, path, method, user, organization, api_key)

        except HTTPException as e:
            # Return rate limit exceeded error
            from fastapi.responses import JSONResponse
            response = JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail},
                headers=getattr(e, 'headers', {})
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

    async def _apply_rate_limit(self, request: Request, path: str, method: str, user, organization, api_key):
        """Apply appropriate rate limiting based on endpoint"""

        # Skip rate limiting for health checks and static files
        if path.startswith('/health') or path.startswith('/metrics') or path.startswith('/docs'):
            return

        # Determine identifier (user ID, API key ID, or IP)
        identifier = self._get_identifier(user, api_key, request)

        # Apply different limits based on endpoint patterns
        if path.startswith('/api/v1/search') or path.startswith('/api/v1/papers'):
            # Search operations
            await self._check_search_limits(identifier, path, user, organization)

        elif path.startswith('/api/v1/rag') or path.startswith('/api/v1/ask'):
            # RAG operations
            await self._check_rag_limits(identifier, path, user, organization, request)

        elif path.startswith('/api/v1/auth'):
            # Auth operations - more lenient
            pass  # Skip rate limiting for auth endpoints

        else:
            # General API operations
            await self._check_general_limits(identifier, path, user, organization)

    def _get_identifier(self, user, api_key, request: Request) -> str:
        """Get identifier for rate limiting"""
        if user and hasattr(user, 'id'):
            return f"user_{user.id}"
        elif api_key and hasattr(api_key, 'id'):
            return f"api_key_{api_key.id}"
        else:
            # Fallback to IP address
            client_ip = getattr(request.client, 'host', 'unknown') if request.client else 'unknown'
            return f"ip_{client_ip}"

    async def _check_search_limits(self, identifier: str, path: str, user, organization):
        """Check rate limits for search operations"""
        async with self.search_limiter:
            allowed, info = await self.search_limiter.check_search_rate_limit(identifier, user, organization)

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Search rate limit exceeded",
                    headers={
                        "X-RateLimit-Remaining": str(info.get("remaining", 0)),
                        "X-RateLimit-Reset": str(int(info.get("reset_time", 0))),
                        "X-RateLimit-Limit": str(info.get("limit", 60)),
                        "Retry-After": str(int(info.get("reset_time", 0) - info.get("reset_time", 0) % 60))
                    }
                )

    async def _check_rag_limits(self, identifier: str, path: str, user, organization, request: Request):
        """Check rate limits for RAG operations"""
        # Check if it's a batch operation
        if 'batch' in path.lower() or request.query_params.get('batch'):
            # Extract batch size if available
            batch_size = 1
            if request.method == 'POST':
                # Try to get batch size from request body (simplified)
                try:
                    body = await request.json()
                    if isinstance(body, list):
                        batch_size = len(body)
                    elif isinstance(body, dict) and 'queries' in body:
                        queries = body['queries']
                        batch_size = len(queries) if isinstance(queries, list) else 1
                except:
                    batch_size = 1

            async with self.rag_limiter:
                allowed, info = await self.rag_limiter.check_rag_batch_rate_limit(
                    identifier, batch_size, user, organization
                )
        elif 'stream' in path.lower():
            # Streaming operation
            async with self.rag_limiter:
                allowed, info = await self.rag_limiter.check_rag_streaming_rate_limit(identifier, user, organization)
        else:
            # Regular RAG operation
            async with self.rag_limiter:
                allowed, info = await self.rag_limiter.check_rag_rate_limit(identifier, user, organization)

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="RAG rate limit exceeded",
                headers={
                    "X-RateLimit-Remaining": str(info.get("remaining", 0)),
                    "X-RateLimit-Reset": str(int(info.get("reset_time", 0))),
                    "X-RateLimit-Limit": str(info.get("limit", 60)),
                    "Retry-After": str(int(info.get("reset_time", 0) - info.get("reset_time", 0) % 60))
                }
            )

    async def _check_general_limits(self, identifier: str, path: str, user, organization):
        """Check rate limits for general API operations"""
        # Use basic rate limiter with user limits
        from ..services.rate_limiting import RateLimiter
        limiter = RateLimiter()

        async with limiter:
            allowed, info = await limiter.check_rate_limit(identifier, path, user=user, organization=organization)

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="API rate limit exceeded",
                    headers={
                        "X-RateLimit-Remaining": str(info.get("remaining", 0)),
                        "X-RateLimit-Reset": str(int(info.get("reset_time", 0))),
                        "X-RateLimit-Limit": str(info.get("limit", 60)),
                        "Retry-After": str(int(info.get("reset_time", 0) - info.get("reset_time", 0) % 60))
                    }
                )