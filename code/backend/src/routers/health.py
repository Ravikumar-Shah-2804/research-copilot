"""
Health check router for comprehensive service monitoring
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.health import health_check_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """Detailed health check with all service statuses"""
    logger.info("Performing detailed health check")
    try:
        health_status = await health_check_service.perform_full_health_check()
        logger.info("Detailed health check completed successfully", status=health_status.get("status"))
        return health_status
    except Exception as e:
        logger.error("Detailed health check failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    logger.debug("Performing readiness check")
    try:
        # Quick check of critical services
        db_healthy = await health_check_service._check_database()
        redis_healthy = await health_check_service._check_redis()

        if db_healthy["status"] == "healthy" and redis_healthy["status"] == "healthy":
            logger.info("Readiness check passed")
            return {"status": "ready"}
        else:
            logger.warning("Readiness check failed", db_status=db_healthy["status"], redis_status=redis_healthy["status"])
            return {"status": "not ready", "issues": [db_healthy, redis_healthy]}

    except Exception as e:
        logger.error("Readiness check error", error=str(e), exc_info=True)
        return {"status": "error", "message": str(e)}


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    # Simple liveness check - if we can respond, we're alive
    logger.debug("Liveness check performed")
    return {"status": "alive"}


@router.get("/services/{service_name}")
async def service_health_check(service_name: str):
    """Check health of a specific service"""
    logger.info("Checking health of specific service", service_name=service_name)
    try:
        readiness = await health_check_service.get_service_readiness(service_name)
        logger.info("Service health check completed", service_name=service_name, status=readiness.get("status"))
        return readiness
    except Exception as e:
        logger.error("Service health check failed", service_name=service_name, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Service health check failed: {str(e)}"
        )


@router.get("/dependencies")
async def service_dependencies():
    """Get service dependency mapping"""
    logger.info("Retrieving service dependencies")
    try:
        dependencies = await health_check_service.get_service_dependencies()
        logger.info("Service dependencies retrieved successfully", dependency_count=len(dependencies))
        return {"dependencies": dependencies}
    except Exception as e:
        logger.error("Failed to get service dependencies", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dependencies: {str(e)}"
        )


@router.get("/metrics")
async def health_metrics():
    """Get health-related metrics"""
    logger.info("Retrieving health metrics")
    try:
        from ..services.monitoring import performance_monitor

        # Get basic health metrics
        perf_metrics = performance_monitor.get_performance_metrics()
        system_metrics = performance_monitor.get_system_metrics()

        logger.info("Health metrics retrieved successfully")
        return {
            "performance": perf_metrics,
            "system": system_metrics,
            "health_checks": {
                "last_check": None,  # Could track this
                "check_interval": health_check_service.check_interval
            }
        }
    except Exception as e:
        logger.error("Failed to get health metrics", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get health metrics: {str(e)}"
        )


@router.get("/status")
async def system_status():
    """Get overall system status"""
    logger.info("Retrieving system status")
    try:
        detailed_health = await health_check_service.perform_full_health_check()

        # Determine overall status based on critical services
        critical_services = ["database", "redis"]
        critical_healthy = all(
            detailed_health["checks"].get(service, {}).get("status") == "healthy"
            for service in critical_services
        )

        status_info = {
            "overall_status": "healthy" if critical_healthy else "unhealthy",
            "critical_services_healthy": critical_healthy,
            "summary": detailed_health["summary"],
            "timestamp": detailed_health["timestamp"],
            "version": "1.0.0",
            "uptime": detailed_health.get("response_time", 0)
        }

        logger.info("System status retrieved", overall_status=status_info["overall_status"])
        return status_info

    except Exception as e:
        logger.error("Failed to get system status", error=str(e), exc_info=True)
        return {
            "overall_status": "error",
            "message": str(e),
            "timestamp": "unknown"
        }