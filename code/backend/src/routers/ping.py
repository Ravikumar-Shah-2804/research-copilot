"""
Health check router
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.cache import RedisCache
from ..services.opensearch import OpenSearchService

router = APIRouter()


@router.get("/ping")
async def ping():
    """Simple ping endpoint"""
    return {"message": "pong"}


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db)
):
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "services": {}
    }

    # Check database
    try:
        result = await db.execute("SELECT 1")
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"

    # Check Redis
    try:
        cache = RedisCache()
        await cache.connect()
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"

    # Check OpenSearch
    try:
        from ..services.embeddings import EmbeddingService
        embedding_service = EmbeddingService()
        opensearch = OpenSearchService(provider=embedding_service.provider)
        await opensearch.connect()
        health_status["services"]["opensearch"] = "healthy"
    except Exception as e:
        health_status["services"]["opensearch"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"

    return health_status


@router.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes/load balancers"""
    # For now, just return healthy
    # In production, check if all dependencies are ready
    return {"status": "ready"}