"""
Performance monitoring and metrics service with Prometheus integration
"""
import time
import logging
import psutil
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from functools import wraps
import json
from datetime import datetime, timedelta

# Prometheus imports
from prometheus_client import (
    Counter, Histogram, Gauge, Summary, Info,
    generate_latest, CONTENT_TYPE_LATEST
)

logger = logging.getLogger(__name__)

# Prometheus metrics
# Request metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code', 'user_type', 'organization']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint', 'status_code']
)

# Business metrics
SEARCH_REQUESTS = Counter(
    'search_requests_total',
    'Total search requests',
    ['search_type', 'user_type', 'organization']
)

RAG_REQUESTS = Counter(
    'rag_requests_total',
    'Total RAG requests',
    ['operation_type', 'user_type', 'organization']
)

API_KEY_USAGE = Counter(
    'api_key_requests_total',
    'Total API key requests',
    ['api_key_id', 'endpoint']
)

# System metrics
ACTIVE_USERS = Gauge(
    'active_users',
    'Number of active users',
    ['organization']
)

SYSTEM_CPU_USAGE = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage'
)

SYSTEM_MEMORY_USAGE = Gauge(
    'system_memory_usage_bytes',
    'System memory usage in bytes'
)

# Database metrics
DB_CONNECTIONS = Gauge(
    'db_connections_active',
    'Number of active database connections'
)

DB_QUERY_LATENCY = Histogram(
    'db_query_duration_seconds',
    'Database query latency',
    ['operation', 'table']
)

# Cache metrics
CACHE_HITS = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

CACHE_MISSES = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

# Error metrics
ERROR_COUNT = Counter(
    'errors_total',
    'Total errors',
    ['error_type', 'endpoint', 'user_type']
)

# Business KPIs
USER_REGISTRATIONS = Counter(
    'user_registrations_total',
    'Total user registrations',
    ['organization', 'registration_method']
)

PAPER_INGESTIONS = Counter(
    'paper_ingestions_total',
    'Total paper ingestions',
    ['source', 'status']
)

# Service health
SERVICE_UP = Gauge(
    'service_up',
    'Service health status',
    ['service_name']
)

# Custom info metric for build info
BUILD_INFO = Info('build_info', 'Build information')


class PerformanceMonitor:
    """Performance monitoring service"""

    def __init__(self):
        self.metrics = {}
        self.request_count = 0
        self.error_count = 0
        self.start_time = time.time()

    @asynccontextmanager
    async def measure_time(self, operation: str, metadata: Optional[Dict[str, Any]] = None):
        """Context manager to measure operation time"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_metric(operation, duration, metadata)

    def record_metric(self, operation: str, duration: float, metadata: Optional[Dict[str, Any]] = None):
        """Record a performance metric"""
        if operation not in self.metrics:
            self.metrics[operation] = {
                "count": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "min_time": float('inf'),
                "max_time": 0.0,
                "last_updated": datetime.now().isoformat()
            }

        metric = self.metrics[operation]
        metric["count"] += 1
        metric["total_time"] += duration
        metric["avg_time"] = metric["total_time"] / metric["count"]
        metric["min_time"] = min(metric["min_time"], duration)
        metric["max_time"] = max(metric["max_time"], duration)
        metric["last_updated"] = datetime.now().isoformat()

        if metadata:
            metric["metadata"] = metadata

        logger.debug(f"Recorded metric: {operation} took {duration:.3f}s")

    def record_request(self, endpoint: str, method: str, status_code: int, duration: float,
                      user_type: str = "anonymous", organization: str = "unknown"):
        """Record API request metrics"""
        self.request_count += 1

        # Update Prometheus metrics
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code),
            user_type=user_type,
            organization=organization
        ).inc()

        REQUEST_LATENCY.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).observe(duration)

        metadata = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "user_type": user_type,
            "organization": organization,
            "timestamp": datetime.now().isoformat()
        }

        if status_code >= 400:
            self.error_count += 1
            ERROR_COUNT.labels(
                error_type="http_error",
                endpoint=endpoint,
                user_type=user_type
            ).inc()

        self.record_metric(f"api_request_{method.lower()}", duration, metadata)

    def record_search_request(self, search_type: str, user_type: str = "anonymous",
                            organization: str = "unknown"):
        """Record search request"""
        SEARCH_REQUESTS.labels(
            search_type=search_type,
            user_type=user_type,
            organization=organization
        ).inc()

    def record_rag_request(self, operation_type: str, user_type: str = "anonymous",
                          organization: str = "unknown"):
        """Record RAG request"""
        RAG_REQUESTS.labels(
            operation_type=operation_type,
            user_type=user_type,
            organization=organization
        ).inc()

    def record_api_key_usage(self, api_key_id: str, endpoint: str):
        """Record API key usage"""
        API_KEY_USAGE.labels(
            api_key_id=api_key_id,
            endpoint=endpoint
        ).inc()

    def record_user_registration(self, organization: str = "unknown", method: str = "direct"):
        """Record user registration"""
        USER_REGISTRATIONS.labels(
            organization=organization,
            registration_method=method
        ).inc()

    def record_paper_ingestion(self, source: str, status: str = "success"):
        """Record paper ingestion"""
        PAPER_INGESTIONS.labels(
            source=source,
            status=status
        ).inc()

    def record_cache_operation(self, operation: str, cache_type: str = "redis"):
        """Record cache operation (hit/miss)"""
        if operation == "hit":
            CACHE_HITS.labels(cache_type=cache_type).inc()
        elif operation == "miss":
            CACHE_MISSES.labels(cache_type=cache_type).inc()

    def record_database_operation(self, operation: str, table: str, duration: float):
        """Record database operation"""
        DB_QUERY_LATENCY.labels(
            operation=operation,
            table=table
        ).observe(duration)

    def update_system_metrics(self):
        """Update system resource metrics"""
        try:
            SYSTEM_CPU_USAGE.set(psutil.cpu_percent(interval=0.1))
            SYSTEM_MEMORY_USAGE.set(psutil.virtual_memory().used)
        except Exception as e:
            logger.error(f"Failed to update system metrics: {e}")

    def update_service_health(self, service_name: str, is_up: bool):
        """Update service health status"""
        SERVICE_UP.labels(service_name=service_name).set(1 if is_up else 0)

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system resource metrics"""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "memory_used_mb": psutil.virtual_memory().used / 1024 / 1024,
                "memory_available_mb": psutil.virtual_memory().available / 1024 / 1024,
                "disk_usage_percent": psutil.disk_usage('/').percent,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {}

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get all performance metrics"""
        uptime = time.time() - self.start_time

        return {
            "uptime_seconds": uptime,
            "total_requests": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.request_count, 1),
            "operations": self.metrics,
            "system": self.get_system_metrics(),
            "timestamp": datetime.now().isoformat()
        }

    def get_search_analytics(self) -> Dict[str, Any]:
        """Get search-specific analytics"""
        search_metrics = {}
        total_search_time = 0
        total_searches = 0

        for operation, data in self.metrics.items():
            if "search" in operation.lower():
                search_metrics[operation] = data
                total_search_time += data["total_time"]
                total_searches += data["count"]

        return {
            "total_searches": total_searches,
            "avg_search_time": total_search_time / max(total_searches, 1),
            "search_operations": search_metrics,
            "timestamp": datetime.now().isoformat()
        }

    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics = {}
        self.request_count = 0
        self.error_count = 0
        self.start_time = time.time()
        logger.info("Performance metrics reset")


class SearchAnalytics:
    """Search analytics and usage tracking"""

    def __init__(self, cache_client=None):
        self.cache = cache_client
        self.analytics_prefix = "analytics:"

    async def record_search_query(
        self,
        query: str,
        mode: str,
        results_count: int,
        search_time: float,
        user_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ):
        """Record search query analytics"""
        try:
            if not self.cache:
                return

            # Record query frequency
            query_key = f"{self.analytics_prefix}query_freq:{query.lower().strip()}"
            await self.cache.set(query_key, 0, ttl=86400 * 30)  # 30 days

            # Record search mode usage
            mode_key = f"{self.analytics_prefix}mode:{mode}"
            await self.cache.set(mode_key, 0, ttl=86400 * 30)

            # Record performance metrics
            perf_key = f"{self.analytics_prefix}performance:{mode}"
            perf_data = {
                "avg_time": search_time,
                "total_queries": 1,
                "last_updated": datetime.now().isoformat()
            }
            await self.cache.set(perf_key, perf_data, ttl=86400 * 7)  # 7 days

            # Record user activity if user_id provided
            if user_id:
                user_key = f"{self.analytics_prefix}user:{user_id}:searches"
                await self.cache.set(user_key, 0, ttl=86400 * 30)

        except Exception as e:
            logger.error(f"Failed to record search analytics: {e}")

    async def get_popular_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular search queries"""
        # This would require a more sophisticated analytics system
        # For now, return placeholder
        return [
            {"query": "machine learning", "count": 150},
            {"query": "deep learning", "count": 120},
            {"query": "neural networks", "count": 95},
            {"query": "computer vision", "count": 80},
            {"query": "nlp", "count": 75}
        ][:limit]

    async def get_search_metrics(self) -> Dict[str, Any]:
        """Get comprehensive search metrics"""
        return {
            "total_searches_24h": 0,  # Would need proper tracking
            "avg_response_time": 0.0,
            "popular_queries": await self.get_popular_queries(5),
            "search_modes_usage": {
                "hybrid": 0,
                "bm25_only": 0,
                "vector_only": 0
            },
            "timestamp": datetime.now().isoformat()
        }


class MonitoringService:
    """Monitoring service for analytics endpoints"""

    def __init__(self):
        self.performance_monitor = PerformanceMonitor()
        self.search_analytics = SearchAnalytics()

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return self.performance_monitor.get_performance_metrics()

    def get_search_analytics(self) -> Dict[str, Any]:
        """Get search analytics"""
        return self.performance_monitor.get_search_analytics()

    def get_prometheus_metrics(self) -> Dict[str, Any]:
        """Get Prometheus metrics"""
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        metrics = generate_latest()
        return {
            "metrics": metrics.decode('utf-8'),
            "format": "prometheus"
        }

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get monitoring dashboard data"""
        return {
            "summary": {
                "total_users": 1250,  # Placeholder
                "active_users_24h": 450,
                "total_papers": 50000,
                "total_searches": 25000
            },
            "charts": {
                "user_growth": [
                    {"date": "2024-01-01", "users": 1000},
                    {"date": "2024-01-02", "users": 1050}
                ],
                "search_trends": [
                    {"date": "2024-01-01", "searches": 500},
                    {"date": "2024-01-02", "searches": 750}
                ]
            },
            "alerts": [
                {
                    "level": "warning",
                    "message": "High memory usage detected",
                    "timestamp": "2024-01-01T12:00:00Z"
                }
            ]
        }


# Global instances
performance_monitor = PerformanceMonitor()
search_analytics = SearchAnalytics()
monitoring_service = MonitoringService()


def monitor_performance(operation: str):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with performance_monitor.measure_time(operation):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


def monitor_api_request():
    """Decorator to monitor API requests"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            # Extract request info from args (FastAPI dependency injection)
            endpoint = getattr(func, '__name__', 'unknown')
            method = 'POST'  # Default assumption

            try:
                result = await func(*args, **kwargs)
                status_code = 200
                return result
            except Exception as e:
                status_code = 500
                raise
            finally:
                duration = time.time() - start_time
                performance_monitor.record_request(endpoint, method, status_code, duration)

        return wrapper
    return decorator