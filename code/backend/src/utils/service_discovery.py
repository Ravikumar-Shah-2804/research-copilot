"""
Service discovery utilities
"""
import logging
import asyncio
from typing import Dict, Optional
import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class ServiceDiscovery:
    """Service discovery for microservices"""

    def __init__(self):
        self.services = {
            "database": {
                "host": settings.db_host,
                "port": settings.db_port,
                "health_endpoint": None
            },
            "redis": {
                "host": settings.redis_host,
                "port": settings.redis_port,
                "health_endpoint": None
            },
            "opensearch": {
                "host": settings.opensearch_host,
                "port": settings.opensearch_port,
                "health_endpoint": "/_cluster/health"
            },
            "openrouter": {
                "host": "openrouter.ai",
                "port": 443,
                "health_endpoint": "/api/v1/models"
            }
        }

    async def check_service_health(self, service_name: str) -> bool:
        """Check if a service is healthy"""
        if service_name not in self.services:
            return False

        service = self.services[service_name]
        if not service["health_endpoint"]:
            # For services without health endpoints, assume healthy
            return True

        try:
            protocol = "https" if service["port"] == 443 else "http"
            url = f"{protocol}://{service['host']}:{service['port']}{service['health_endpoint']}"

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                return response.status_code == 200

        except Exception as e:
            logger.warning(f"Service {service_name} health check failed: {e}")
            return False

    async def get_service_url(self, service_name: str) -> Optional[str]:
        """Get service URL"""
        if service_name not in self.services:
            return None

        service = self.services[service_name]
        protocol = "https" if service["port"] == 443 else "http"
        return f"{protocol}://{service['host']}:{service['port']}"

    async def discover_all_services(self) -> Dict[str, bool]:
        """Discover and check all services"""
        results = {}
        for service_name in self.services:
            results[service_name] = await self.check_service_health(service_name)
        return results

    def get_service_config(self, service_name: str) -> Optional[Dict]:
        """Get service configuration"""
        return self.services.get(service_name)


# Global service discovery instance
service_discovery = ServiceDiscovery()