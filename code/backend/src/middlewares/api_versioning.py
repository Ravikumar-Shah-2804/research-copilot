"""
API versioning middleware
"""
import re
from typing import Callable, Optional, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse


class APIVersioningMiddleware:
    """Middleware for API versioning support"""

    def __init__(self, app: Callable, default_version: str = "v1"):
        self.app = app
        self.default_version = default_version
        self.supported_versions = ["v1", "v2"]  # Add more versions as needed

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Extract API version from URL path or Accept header
        version = self._extract_version(request)

        if version and version not in self.supported_versions:
            response = JSONResponse(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                content={
                    "detail": f"API version '{version}' is not supported. Supported versions: {', '.join(self.supported_versions)}"
                }
            )
            await response(scope, receive, send)
            return

        # Set version in request state
        request.state.api_version = version or self.default_version

        await self.app(scope, receive, send)

    def _extract_version(self, request: Request) -> Optional[str]:
        """Extract API version from request"""
        path = request.url.path

        # Check URL path for version (e.g., /api/v1/endpoint)
        version_match = re.match(r'/api/(v\d+)/', path)
        if version_match:
            return version_match.group(1)

        # Check Accept header for version (e.g., application/vnd.api.v1+json)
        accept_header = request.headers.get("Accept", "")
        version_match = re.search(r'application/vnd\.api\.(\w+)\+json', accept_header)
        if version_match:
            return version_match.group(1)

        # Check custom header
        version_header = request.headers.get("X-API-Version")
        if version_header:
            return version_header

        return None


class RequestTransformationMiddleware:
    """Middleware for request/response transformation"""

    def __init__(self, app: Callable):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Transform request based on API version
        api_version = getattr(request.state, 'api_version', 'v1')
        transformed_request = await self._transform_request(request, api_version)

        # Store transformed request
        scope["transformed_request"] = transformed_request

        async def send_with_transformation(message):
            if message["type"] == "http.response.start":
                # Could transform response headers here
                pass
            elif message["type"] == "http.response.body":
                # Could transform response body here based on API version
                api_version = getattr(request.state, 'api_version', 'v1')
                message = await self._transform_response(message, api_version)

            await send(message)

        await self.app(scope, receive, send_with_transformation)

    async def _transform_request(self, request: Request, api_version: str) -> Request:
        """Transform request based on API version"""
        # For now, just return the original request
        # In a real implementation, you might:
        # - Transform field names
        # - Add default values
        # - Convert data formats
        # - Handle deprecated parameters

        if api_version == "v2":
            # Example: In v2, we might expect different field names
            # This would require parsing the request body and transforming it
            pass

        return request

    async def _transform_response(self, message: Dict[str, Any], api_version: str) -> Dict[str, Any]:
        """Transform response based on API version"""
        # For now, just return the original message
        # In a real implementation, you might:
        # - Change field names
        # - Add/remove fields
        # - Convert data formats
        # - Add deprecation warnings

        return message


class APIRoutingMiddleware:
    """Middleware for advanced API routing"""

    def __init__(self, app: Callable):
        self.app = app
        self.route_mappings = {
            # Example route mappings for different versions
            "v1": {
                "/api/v1/legacy-endpoint": "/api/v1/new-endpoint"
            },
            "v2": {
                "/api/v2/beta-feature": "/api/v2/stable-feature"
            }
        }

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        path = request.url.path

        # Check for route mappings
        api_version = getattr(request.state, 'api_version', 'v1')
        version_mappings = self.route_mappings.get(api_version, {})

        if path in version_mappings:
            # Redirect to new route
            new_path = version_mappings[path]
            scope["path"] = new_path.encode()

            # Log the routing
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Routed {path} to {new_path} for API version {api_version}")

        await self.app(scope, receive, send)