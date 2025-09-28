"""
Enhanced error handling middleware with retry capabilities
"""
import logging
import traceback
from typing import Callable, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from httpx import TimeoutException, ConnectError

from ..utils.exceptions import (
    ResearchCopilotException,
    NotFoundError,
    ValidationError,
    PermissionDeniedError,
    AuthenticationError,
    AuthorizationError
)
from ..services.audit import audit_service
from ..models.audit import AuditEvent

logger = logging.getLogger(__name__)


class EnhancedErrorHandlingMiddleware:
    """Middleware for comprehensive error handling and logging"""

    def __init__(self, app: Callable):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        async def send_with_error_handling(message):
            if message["type"] == "http.response.start":
                # Could modify response headers here
                pass
            await send(message)

        try:
            await self.app(scope, receive, send_with_error_handling)

        except Exception as exc:
            # Handle the exception and return appropriate response
            response = await self._handle_exception(request, exc)
            await response(scope, receive, send)

    async def _handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle exceptions and return appropriate JSON responses"""

        # Extract request information for logging
        request_info = self._extract_request_info(request)

        # Determine error type and create appropriate response
        if isinstance(exc, HTTPException):
            # FastAPI HTTPException - preserve original behavior
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=getattr(exc, 'headers', {})
            )

        elif isinstance(exc, NotFoundError):
            await self._log_error(request_info, exc, "NOT_FOUND")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Resource not found", "type": "NOT_FOUND"}
            )

        elif isinstance(exc, ValidationError):
            await self._log_error(request_info, exc, "VALIDATION_ERROR")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Validation error", "type": "VALIDATION_ERROR"}
            )

        elif isinstance(exc, (AuthenticationError, AuthorizationError)):
            await self._log_security_event(request_info, exc)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication required", "type": "AUTHENTICATION_ERROR"},
                headers={"WWW-Authenticate": "Bearer"}
            )

        elif isinstance(exc, PermissionDeniedError):
            await self._log_security_event(request_info, exc)
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Permission denied", "type": "PERMISSION_DENIED"}
            )

        elif isinstance(exc, (OperationalError, SQLAlchemyError)):
            await self._log_error(request_info, exc, "DATABASE_ERROR")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Database temporarily unavailable", "type": "DATABASE_ERROR"}
            )

        elif isinstance(exc, (TimeoutException, ConnectError)):
            await self._log_error(request_info, exc, "NETWORK_ERROR")
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={"detail": "Service temporarily unavailable", "type": "NETWORK_ERROR"}
            )

        elif isinstance(exc, ResearchCopilotException):
            await self._log_error(request_info, exc, "APPLICATION_ERROR")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Application error", "type": "APPLICATION_ERROR"}
            )

        else:
            # Unexpected error - log with full traceback
            await self._log_unexpected_error(request_info, exc)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error", "type": "INTERNAL_ERROR"}
            )

    def _extract_request_info(self, request: Request) -> Dict[str, Any]:
        """Extract relevant information from the request"""
        return {
            "method": request.method,
            "url": str(request.url),
            "endpoint": request.url.path,
            "query_params": dict(request.query_params),
            "user_agent": request.headers.get("User-Agent"),
            "ip_address": getattr(request.client, 'host', None) if request.client else None,
            "correlation_id": getattr(request.state, 'correlation_id', None),
            "user_id": getattr(request.state, 'user', None),
            "organization_id": getattr(request.state, 'organization_obj', None)
        }

    async def _log_error(self, request_info: Dict[str, Any], exc: Exception, error_type: str):
        """Log application errors"""
        logger.error(
            f"Application error: {error_type}",
            extra={
                "error_type": error_type,
                "error_message": str(exc),
                "request_info": request_info,
                "correlation_id": request_info.get("correlation_id"),
                "traceback": traceback.format_exc()
            }
        )

        # Create audit event for significant errors
        if error_type in ["DATABASE_ERROR", "NETWORK_ERROR", "APPLICATION_ERROR"]:
            await audit_service.log_event_async(
                AuditEvent(
                    action="system_error",
                    resource_type="system",
                    success=False,
                    error_message=str(exc),
                    metadata={
                        "error_type": error_type,
                        "endpoint": request_info.get("endpoint"),
                        "method": request_info.get("method")
                    },
                    compliance_level="critical" if error_type == "DATABASE_ERROR" else "standard"
                ),
                request_info
            )

    async def _log_security_event(self, request_info: Dict[str, Any], exc: Exception):
        """Log security-related events"""
        logger.warning(
            f"Security event: {type(exc).__name__}",
            extra={
                "error_type": "SECURITY_EVENT",
                "error_message": str(exc),
                "request_info": request_info,
                "correlation_id": request_info.get("correlation_id"),
                "ip_address": request_info.get("ip_address"),
                "user_agent": request_info.get("user_agent")
            }
        )

        # Create audit event for security events
        await audit_service.log_event_async(
            AuditEvent(
                action="security_violation",
                resource_type="security",
                success=False,
                error_message=str(exc),
                metadata={
                    "violation_type": type(exc).__name__,
                    "endpoint": request_info.get("endpoint"),
                    "ip_address": request_info.get("ip_address")
                },
                compliance_level="critical"
            ),
            request_info
        )

    async def _log_unexpected_error(self, request_info: Dict[str, Any], exc: Exception):
        """Log unexpected errors with full details"""
        logger.critical(
            "Unexpected error occurred",
            extra={
                "error_type": "UNEXPECTED_ERROR",
                "error_message": str(exc),
                "request_info": request_info,
                "correlation_id": request_info.get("correlation_id"),
                "traceback": traceback.format_exc()
            }
        )

        # Create audit event for unexpected errors
        await audit_service.log_event_async(
            AuditEvent(
                action="unexpected_error",
                resource_type="system",
                success=False,
                error_message=str(exc),
                metadata={
                    "endpoint": request_info.get("endpoint"),
                    "traceback": traceback.format_exc()[:1000]  # Limit traceback size
                },
                compliance_level="critical"
            ),
            request_info
        )


class GracefulDegradationMiddleware:
    """Middleware for graceful degradation when services are unavailable"""

    def __init__(self, app: Callable):
        self.app = app
        self.degraded_services = set()  # Track which services are degraded

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        path = request.url.path

        # Check if we should degrade response for this endpoint
        if await self._should_degrade_response(path):
            response = await self._create_degraded_response(path)
            await response(scope, receive, send)
            return

        # Check if we should add degradation headers
        async def send_with_degradation_info(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                if self.degraded_services:
                    headers.append([
                        b"X-Service-Degradation",
                        f"Some services unavailable: {', '.join(self.degraded_services)}".encode()
                    ])
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_degradation_info)
        except Exception as exc:
            # If main application fails, try degraded response
            if await self._can_serve_degraded(path):
                response = await self._create_degraded_response(path)
                await response(scope, receive, send)
                return
            else:
                raise

    async def _should_degrade_response(self, path: str) -> bool:
        """Determine if we should serve a degraded response"""
        # Example logic: degrade non-critical endpoints when critical services are down
        critical_services_down = {"database", "cache"}.intersection(self.degraded_services)

        if critical_services_down and path.startswith(("/api/v1/search", "/api/v1/rag")):
            return True

        return False

    async def _can_serve_degraded(self, path: str) -> bool:
        """Check if we can serve a degraded response for this endpoint"""
        # Define which endpoints can serve degraded responses
        degradable_endpoints = [
            "/health",
            "/api/v1/search",
            "/api/v1/analytics"
        ]

        return any(path.startswith(endpoint) for endpoint in degradable_endpoints)

    async def _create_degraded_response(self, path: str) -> JSONResponse:
        """Create a degraded response for the endpoint"""
        if path == "/health":
            return JSONResponse(
                status_code=200,
                content={
                    "status": "degraded",
                    "message": "Some services are unavailable",
                    "degraded_services": list(self.degraded_services)
                }
            )
        elif path.startswith("/api/v1/search"):
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Search service temporarily unavailable",
                    "type": "SERVICE_DEGRADED",
                    "retry_after": 30
                },
                headers={"Retry-After": "30"}
            )
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Service temporarily unavailable",
                    "type": "SERVICE_DEGRADED"
                }
            )

    def mark_service_degraded(self, service_name: str):
        """Mark a service as degraded"""
        self.degraded_services.add(service_name)
        logger.warning(f"Service marked as degraded: {service_name}")

    def mark_service_healthy(self, service_name: str):
        """Mark a service as healthy"""
        self.degraded_services.discard(service_name)
        logger.info(f"Service marked as healthy: {service_name}")