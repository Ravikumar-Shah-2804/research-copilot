"""
Input validation and sanitization middleware
"""
import re
import logging
from typing import Callable, Dict, Any, List
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import bleach
import json

logger = logging.getLogger(__name__)


class InputValidationMiddleware:
    """Middleware for input validation and sanitization"""

    def __init__(self, app: Callable):
        self.app = app
        # Common SQL injection patterns
        self.sql_injection_patterns = [
            r';\s*--',  # Semicolon followed by comment
            r';\s*/\*',  # Semicolon followed by block comment start
            r'union\s+select',  # UNION SELECT
            r'/\*.*\*/',  # Block comments
            r'--.*$',  # Line comments
            r';\s*drop\s+table',  # DROP TABLE
            r';\s*delete\s+from',  # DELETE FROM
            r';\s*update\s+.*set',  # UPDATE SET
            r';\s*insert\s+into',  # INSERT INTO
        ]

        # XSS patterns
        self.xss_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',  # JavaScript URLs
            r'on\w+\s*=',  # Event handlers
            r'<iframe[^>]*>.*?</iframe>',  # Iframe tags
            r'<object[^>]*>.*?</object>',  # Object tags
            r'<embed[^>]*>.*?</embed>',  # Embed tags
        ]

        # Path traversal patterns
        self.path_traversal_patterns = [
            r'\.\./',  # Directory traversal
            r'\.\.\\',  # Windows directory traversal
            r'%2e%2e%2f',  # URL encoded ../
            r'%2e%2e%5c',  # URL encoded ..\
        ]

        # Maximum sizes
        self.max_query_length = 1000
        self.max_body_size = 10 * 1024 * 1024  # 10MB
        self.max_header_value_length = 4096

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        try:
            # Validate request
            await self._validate_request(request)

            # Sanitize input if needed
            await self._sanitize_request(request)

        except HTTPException as e:
            # Return error response
            response = JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
            await response(scope, receive, send)
            return
        except Exception as e:
            logger.error(f"Input validation error: {e}")
            response = JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid request"}
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

    async def _validate_request(self, request: Request):
        """Validate request parameters"""
        # Check query parameters
        for key, value in request.query_params.items():
            if len(value) > self.max_query_length:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Query parameter '{key}' too long"
                )

            # Check for malicious patterns
            if self._contains_malicious_patterns(value):
                logger.warning(f"Malicious pattern detected in query parameter: {key}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid query parameter"
                )

        # Check headers
        for header_name, header_value in request.headers.items():
            if len(header_value) > self.max_header_value_length:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Header '{header_name}' too long"
                )

        # Check path parameters
        path = request.url.path
        if self._contains_path_traversal(path):
            logger.warning(f"Path traversal attempt detected: {path}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid path"
            )

        # Check request body size (if available)
        content_length = request.headers.get('content-length')
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_body_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Request body too large"
                    )
            except ValueError:
                pass

    async def _sanitize_request(self, request: Request):
        """Sanitize request input"""
        # Sanitize query parameters
        sanitized_query = {}
        for key, value in request.query_params.items():
            sanitized_query[key] = self._sanitize_string(value)

        # Update request with sanitized query params
        # Note: This is a simplified approach. In a real implementation,
        # you might need to modify the request object or use a custom request class

    def _contains_malicious_patterns(self, value: str) -> bool:
        """Check if string contains malicious patterns"""
        all_patterns = (
            self.sql_injection_patterns +
            self.xss_patterns +
            self.path_traversal_patterns
        )

        for pattern in all_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    def _contains_path_traversal(self, path: str) -> bool:
        """Check if path contains traversal patterns"""
        for pattern in self.path_traversal_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                return True
        return False

    def _sanitize_string(self, value: str) -> str:
        """Sanitize string input"""
        if not value:
            return value

        # Remove null bytes
        value = value.replace('\x00', '')

        # HTML sanitize
        value = bleach.clean(value, strip=True)

        # Remove control characters except whitespace
        value = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n\r')

        return value


class ContentTypeValidationMiddleware:
    """Middleware to validate content types"""

    def __init__(self, app: Callable, allowed_content_types: List[str] = None):
        self.app = app
        self.allowed_content_types = allowed_content_types or [
            'application/json',
            'application/x-www-form-urlencoded',
            'multipart/form-data',
            'text/plain'
        ]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        content_type = request.headers.get('content-type', '').lower()

        # Allow requests without content-type (GET, HEAD, etc.)
        if not content_type:
            await self.app(scope, receive, send)
            return

        # Extract main content type
        main_type = content_type.split(';')[0].strip()

        if main_type not in self.allowed_content_types:
            logger.warning(f"Invalid content type: {content_type}")
            response = JSONResponse(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                content={"detail": f"Content type '{main_type}' not allowed"}
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


class RateLimitValidationMiddleware:
    """Middleware to validate rate limit headers"""

    def __init__(self, app: Callable):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # This middleware can add rate limit headers to responses
        # The actual rate limiting is handled by the rate limiting service

        async def send_with_rate_limit_headers(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])

                # Add rate limit headers if available in request state
                request = Request(scope, receive)
                if hasattr(request.state, 'rate_limit_info'):
                    rate_info = request.state.rate_limit_info
                    headers.extend([
                        [b"X-RateLimit-Limit", str(rate_info.get('limit', '')).encode()],
                        [b"X-RateLimit-Remaining", str(rate_info.get('remaining', '')).encode()],
                        [b"X-RateLimit-Reset", str(rate_info.get('reset_time', '')).encode()],
                    ])

                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_with_rate_limit_headers)