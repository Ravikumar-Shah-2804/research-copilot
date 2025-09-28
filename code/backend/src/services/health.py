"""
Comprehensive health check service for all system components
"""
import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from ..database import check_database_health
from ..services.cache import RedisCache
from ..services.opensearch import OpenSearchService
from ..services.monitoring import performance_monitor
from ..utils.service_discovery import service_discovery

logger = logging.getLogger(__name__)


class HealthCheckService:
    """Service for comprehensive health checking"""

    def __init__(self):
        self.last_checks = {}
        self.check_interval = 30  # seconds
        self.service_timeouts = {
            "database": 5.0,
            "redis": 3.0,
            "opensearch": 5.0,
            "openrouter": 10.0
        }

    async def perform_full_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check of all services"""
        start_time = time.time()

        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {},
            "summary": {
                "total_services": 0,
                "healthy_services": 0,
                "unhealthy_services": 0,
                "degraded_services": 0
            }
        }

        # Check all services
        services_to_check = [
            ("database", self._check_database),
            ("redis", self._check_redis),
            ("opensearch", self._check_opensearch),
            ("openrouter", self._check_openrouter),
            ("performance_monitor", self._check_performance_monitor),
            ("circuit_breakers", self._check_circuit_breakers)
        ]

        health_status["summary"]["total_services"] = len(services_to_check)

        for service_name, check_func in services_to_check:
            try:
                check_result = await check_func()
                health_status["checks"][service_name] = check_result

                if check_result["status"] == "healthy":
                    health_status["summary"]["healthy_services"] += 1
                elif check_result["status"] == "degraded":
                    health_status["summary"]["degraded_services"] += 1
                else:
                    health_status["summary"]["unhealthy_services"] += 1

            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                health_status["checks"][service_name] = {
                    "status": "error",
                    "message": str(e),
                    "response_time": 0.0,
                    "timestamp": datetime.utcnow().isoformat()
                }
                health_status["summary"]["unhealthy_services"] += 1

        # Determine overall status
        if health_status["summary"]["unhealthy_services"] > 0:
            health_status["status"] = "unhealthy"
        elif health_status["summary"]["degraded_services"] > 0:
            health_status["status"] = "degraded"

        health_status["response_time"] = time.time() - start_time

        return health_status

    async def _check_database(self) -> Dict[str, Any]:
        """Check database health"""
        start_time = time.time()

        try:
            is_healthy = await check_database_health()
            response_time = time.time() - start_time

            if is_healthy:
                return {
                    "status": "healthy",
                    "message": "Database connection successful",
                    "response_time": response_time,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Database connection failed",
                    "response_time": response_time,
                    "timestamp": datetime.utcnow().isoformat()
                }

        except Exception as e:
            response_time = time.time() - start_time
            return {
                "status": "error",
                "message": f"Database health check error: {str(e)}",
                "response_time": response_time,
                "timestamp": datetime.utcnow().isoformat()
            }

    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis health"""
        start_time = time.time()

        try:
            cache = RedisCache()
            await cache.connect()

            # Simple ping test
            pong = await cache.ping()
            await cache.disconnect()

            response_time = time.time() - start_time

            if pong:
                return {
                    "status": "healthy",
                    "message": "Redis connection successful",
                    "response_time": response_time,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Redis ping failed",
                    "response_time": response_time,
                    "timestamp": datetime.utcnow().isoformat()
                }

        except Exception as e:
            response_time = time.time() - start_time
            return {
                "status": "error",
                "message": f"Redis health check error: {str(e)}",
                "response_time": response_time,
                "timestamp": datetime.utcnow().isoformat()
            }

    async def _check_opensearch(self) -> Dict[str, Any]:
        """Check OpenSearch health"""
        start_time = time.time()

        try:
            from .embeddings import EmbeddingService
            embedding_service = EmbeddingService()
            opensearch = OpenSearchService(provider=embedding_service.provider)
            await opensearch.connect()

            # Get cluster health
            health = await opensearch.client.cluster.health()
            await opensearch.disconnect()

            response_time = time.time() - start_time
            cluster_status = health.get("status", "unknown")

            if cluster_status in ["green", "yellow"]:
                status = "healthy"
            elif cluster_status == "red":
                status = "unhealthy"
            else:
                status = "unknown"

            return {
                "status": status,
                "message": f"OpenSearch cluster status: {cluster_status}",
                "response_time": response_time,
                "details": {
                    "cluster_status": cluster_status,
                    "number_of_nodes": health.get("number_of_nodes"),
                    "active_shards": health.get("active_shards")
                },
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            response_time = time.time() - start_time
            return {
                "status": "error",
                "message": f"OpenSearch health check error: {str(e)}",
                "response_time": response_time,
                "timestamp": datetime.utcnow().isoformat()
            }

    async def _check_openrouter(self) -> Dict[str, Any]:
        """Check OpenRouter API health"""
        start_time = time.time()

        try:
            is_healthy = await service_discovery.check_service_health("openrouter")
            response_time = time.time() - start_time

            if is_healthy:
                return {
                    "status": "healthy",
                    "message": "OpenRouter API accessible",
                    "response_time": response_time,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "degraded",
                    "message": "OpenRouter API not accessible",
                    "response_time": response_time,
                    "timestamp": datetime.utcnow().isoformat()
                }

        except Exception as e:
            response_time = time.time() - start_time
            return {
                "status": "error",
                "message": f"OpenRouter health check error: {str(e)}",
                "response_time": response_time,
                "timestamp": datetime.utcnow().isoformat()
            }

    async def _check_performance_monitor(self) -> Dict[str, Any]:
        """Check performance monitoring system"""
        try:
            metrics = performance_monitor.get_performance_metrics()

            return {
                "status": "healthy",
                "message": "Performance monitoring active",
                "details": {
                    "uptime_seconds": metrics.get("uptime_seconds"),
                    "total_requests": metrics.get("total_requests"),
                    "error_rate": metrics.get("error_rate")
                },
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Performance monitor check error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }

    async def _check_circuit_breakers(self) -> Dict[str, Any]:
        """Check circuit breaker status"""
        try:
            from ..services.circuit_breaker import circuit_breaker_registry
            stats = circuit_breaker_registry.get_all_stats()

            # Check if any circuit breakers are open
            open_breakers = [
                name for name, stat in stats.items()
                if stat.get("state") == "open"
            ]

            if open_breakers:
                return {
                    "status": "degraded",
                    "message": f"Circuit breakers open: {', '.join(open_breakers)}",
                    "details": stats,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "healthy",
                    "message": "All circuit breakers closed",
                    "details": stats,
                    "timestamp": datetime.utcnow().isoformat()
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Circuit breaker check error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }

    async def get_service_dependencies(self) -> Dict[str, List[str]]:
        """Get service dependency mapping"""
        return {
            "api": ["database", "redis", "opensearch"],
            "search": ["opensearch", "redis"],
            "rag": ["openrouter", "redis", "database"],
            "analytics": ["database", "redis"],
            "admin": ["database", "redis"]
        }

    async def get_service_readiness(self, service_name: str) -> Dict[str, Any]:
        """Check if a specific service is ready"""
        check_functions = {
            "database": self._check_database,
            "redis": self._check_redis,
            "opensearch": self._check_opensearch,
            "openrouter": self._check_openrouter
        }

        if service_name not in check_functions:
            return {
                "service": service_name,
                "ready": False,
                "message": f"Unknown service: {service_name}"
            }

        try:
            result = await check_functions[service_name]()
            return {
                "service": service_name,
                "ready": result["status"] == "healthy",
                "status": result["status"],
                "message": result["message"],
                "response_time": result.get("response_time", 0.0)
            }
        except Exception as e:
            return {
                "service": service_name,
                "ready": False,
                "status": "error",
                "message": str(e)
            }


class HealthService:
    """Health service for analytics endpoints"""

    def __init__(self):
        self.health_check_service = HealthCheckService()

    async def get_system_health(self) -> Dict[str, Any]:
        """Get system health"""
        return await self.health_check_service.perform_full_health_check()


# Global health check service instance
health_check_service = HealthCheckService()
health_service = HealthService()