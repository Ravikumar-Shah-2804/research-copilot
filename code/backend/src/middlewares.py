"""
Custom middleware for Research Copilot
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from .config import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """Middleware to add security headers"""

    def __init__(self, app: Callable):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                # Add security headers
                headers.extend([
                    [b"X-Content-Type-Options", b"nosniff"],
                    [b"X-Frame-Options", b"DENY"],
                    [b"X-XSS-Protection", b"1; mode=block"],
                    [b"Strict-Transport-Security", b"max-age=31536000; includeSubDomains"],
                    [b"Content-Security-Policy", b"default-src 'self'"],
                    [b"Referrer-Policy", b"strict-origin-when-cross-origin"],
                ])
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_security_headers)


class DistributedTracingMiddleware:
    """Middleware for distributed tracing with correlation IDs"""

    def __init__(self, app: Callable):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import uuid
        from fastapi import Request

        # Create request object to access headers
        request = Request(scope, receive)

        # Extract correlation IDs from request headers
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        incoming_span_id = request.headers.get("X-Span-ID")

        # Generate span ID for this request
        span_id = str(uuid.uuid4())[:16]  # Short span ID

        # Add tracing information to scope
        scope["correlation_id"] = correlation_id
        scope["trace_id"] = trace_id
        scope["span_id"] = span_id
        scope["parent_span_id"] = incoming_span_id

        # Set tracing context in request state (will be available in handlers)
        async def set_tracing_context():
            # This will be called after the request object is created
            pass

        async def send_with_tracing_headers(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                # Inject correlation IDs into response headers
                headers.extend([
                    [b"X-Correlation-ID", correlation_id.encode()],
                    [b"X-Trace-ID", trace_id.encode()],
                    [b"X-Span-ID", span_id.encode()],
                ])
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_tracing_headers)


class TimeoutMiddleware:
    """Middleware to handle request timeouts"""

    def __init__(self, app: Callable, timeout: int = 30):
        self.app = app
        self.timeout = timeout

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import asyncio
        from asyncio import TimeoutError

        try:
            await asyncio.wait_for(
                self.app(scope, receive, send),
                timeout=self.timeout
            )
        except TimeoutError:
            logger.warning(f"Request timeout after {self.timeout} seconds")
            await send({
                "type": "http.response.start",
                "status": 408,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({
                "type": "http.response.body",
                "body": b'{"detail": "Request timeout"}',
            })


def setup_middlewares(app):
    """Setup all custom middlewares"""
    # API gateway features (must be early) - commented out for testing
    # from .api_versioning import APIVersioningMiddleware, RequestTransformationMiddleware, APIRoutingMiddleware
    # app.add_middleware(APIVersioningMiddleware, default_version="v1")
    # app.add_middleware(RequestTransformationMiddleware)
    # app.add_middleware(APIRoutingMiddleware)

    # Input validation
    # from .validation import InputValidationMiddleware, ContentTypeValidationMiddleware, RateLimitValidationMiddleware
    # app.add_middleware(InputValidationMiddleware)
    # app.add_middleware(ContentTypeValidationMiddleware)
    # app.add_middleware(RateLimitValidationMiddleware)

    # Organization isolation - commented out for testing
    # from .organization import OrganizationIsolationMiddleware
    # app.add_middleware(OrganizationIsolationMiddleware)

    # API key authentication - commented out for testing
    # from .api_key_auth import APIKeyAuthMiddleware
    # app.add_middleware(APIKeyAuthMiddleware)

    # Tiered rate limiting - commented out for testing
    # from .tiered_rate_limit import TieredRateLimitMiddleware
    # app.add_middleware(TieredRateLimitMiddleware)

    # Security headers - commented out for testing
    # app.add_middleware(SecurityHeadersMiddleware)

    # Distributed tracing
    app.add_middleware(DistributedTracingMiddleware)

    # Enhanced error handling - commented out for testing
    # from .error_handling import EnhancedErrorHandlingMiddleware, GracefulDegradationMiddleware
    # app.add_middleware(EnhancedErrorHandlingMiddleware)
    # app.add_middleware(GracefulDegradationMiddleware)

    # Timeout middleware (30 seconds) - commented out for testing
    # app.add_middleware(TimeoutMiddleware, timeout=30)
