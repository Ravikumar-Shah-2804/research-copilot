"""
Analytics and monitoring router for admin operations
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID


from ..database import get_db
from ..models.user import User
from ..services.auth import get_current_active_user, require_admin
from ..services.monitoring import performance_monitor, search_analytics
from ..services.rate_limiting import search_rate_limiter
from ..services.audit import audit_logger

router = APIRouter()


@router.get("/performance")
async def get_performance_metrics(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get system performance metrics"""
    try:
        return performance_monitor.get_performance_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")


@router.get("/search-analytics")
async def get_search_analytics(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get search analytics"""
    try:
        return await search_analytics.get_search_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get search analytics: {str(e)}")


@router.get("/rate-limits/{user_id}")
async def get_user_rate_limits(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get rate limit status for a user"""
    try:
        async with search_rate_limiter:
            info = await search_rate_limiter.get_rate_limit_info(user_id, "search")
            return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rate limit info: {str(e)}")


@router.post("/rate-limits/{user_id}/reset")
async def reset_user_rate_limits(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Reset rate limits for a user"""
    try:
        async with search_rate_limiter:
            await search_rate_limiter.reset_rate_limit(user_id, "search")
            return {"message": f"Rate limits reset for user {user_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset rate limits: {str(e)}")


@router.get("/audit-trail")
async def get_audit_trail(
    user_id: str = None,
    event_type: str = None,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get audit trail (placeholder - would need proper implementation)"""
    try:
        # This would need proper log aggregation
        return {
            "message": "Audit trail retrieval not fully implemented",
            "user_id": user_id,
            "event_type": event_type,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get audit trail: {str(e)}")


@router.post("/cache/clear")
async def clear_search_cache(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Clear search result cache"""
    try:
        from ..services.cache import RedisCache
        cache = RedisCache()
        await cache.connect()
        await cache.clear()
        await cache.disconnect()
        return {"message": "Search cache cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


@router.get("/health")
async def system_health_check(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """System health check"""
    try:
        health_status = {
            "status": "healthy",
            "services": {
                "database": "unknown",  # Would need DB health check
                "opensearch": "unknown",  # Would need OpenSearch health check
                "redis": "unknown",  # Would need Redis health check
                "embeddings": "unknown"  # Would need embedding service health check
            },
            "metrics": performance_monitor.get_system_metrics()
        }

        return health_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/metrics")
async def get_prometheus_metrics(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get Prometheus metrics (admin only)"""
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        from fastapi.responses import Response

        metrics_data = generate_latest()
        return Response(
            content=metrics_data,
            media_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/monitoring/dashboard")
async def get_monitoring_dashboard(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get monitoring dashboard data"""
    try:
        # Get various metrics for dashboard
        performance_metrics = performance_monitor.get_performance_metrics()
        system_metrics = performance_monitor.get_system_metrics()
        search_analytics = await performance_monitor.get_search_metrics()

        # Get active users count (simplified)
        from sqlalchemy import func
        from ..models.user import User
        active_users_result = await db.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )
        active_users = active_users_result.scalar()

        dashboard_data = {
            "timestamp": datetime.now().isoformat(),
            "system": {
                **system_metrics,
                "active_users": active_users
            },
            "performance": performance_metrics,
            "search": search_analytics,
            "alerts": []  # Could be populated with alerting logic
        }

        return dashboard_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard data: {str(e)}")


@router.get("/usage/user/{user_id}")
async def get_user_usage(
    user_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get usage analytics for a user"""
    # Permission check
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot view other users' usage"
        )

    # Default to last 30 days if not specified
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    try:
        from ..services.usage import usage_analytics_service
        usage = await usage_analytics_service.get_user_usage(db, user_id, start_date, end_date)
        return usage
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user usage: {str(e)}")


@router.get("/usage/organization/{org_id}")
async def get_organization_usage(
    org_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get usage analytics for an organization"""
    # Permission check
    if not current_user.is_superuser and current_user.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot view other organizations' usage"
        )

    # Default to last 30 days if not specified
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    try:
        from ..services.usage import usage_analytics_service
        usage = await usage_analytics_service.get_organization_usage(db, org_id, start_date, end_date)
        return usage
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get organization usage: {str(e)}")


@router.get("/billing/{org_id}")
async def get_billing_info(
    org_id: UUID,
    billing_period_start: Optional[datetime] = None,
    billing_period_end: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get billing information for an organization"""
    # Permission check
    if not current_user.is_superuser and current_user.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot view other organizations' billing"
        )

    # Default to current month if not specified
    if not billing_period_end:
        billing_period_end = datetime.utcnow()
    if not billing_period_start:
        billing_period_start = billing_period_end.replace(day=1)  # First day of current month

    try:
        from ..services.usage import usage_analytics_service
        billing = await usage_analytics_service.calculate_billing_metrics(
            db, org_id, billing_period_start, billing_period_end
        )
        return billing
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get billing info: {str(e)}")


@router.get("/usage/trends")
async def get_usage_trends(
    user_id: Optional[UUID] = None,
    organization_id: Optional[UUID] = None,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get usage trends over time"""
    # Permission check
    if not user_id and not organization_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser privileges required to access global usage trends")
    if user_id and not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot view other users' trends"
        )
    if organization_id and not current_user.is_superuser and current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot view other organizations' trends"
        )

    try:
        from ..services.usage import usage_analytics_service
        trends = await usage_analytics_service.get_usage_trends(
            db, user_id, organization_id, days
        )
        return trends
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get usage trends: {str(e)}")


@router.get("/billing/invoice/{org_id}")
async def generate_invoice(
    org_id: UUID,
    billing_period_start: Optional[datetime] = None,
    billing_period_end: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate invoice data for an organization"""
    # Permission check
    if not current_user.is_superuser and current_user.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot generate invoices for other organizations"
        )

    # Default to current month if not specified
    if not billing_period_end:
        billing_period_end = datetime.utcnow()
    if not billing_period_start:
        billing_period_start = billing_period_end.replace(day=1)

    try:
        from ..services.usage import usage_analytics_service

        # Get billing metrics
        billing = await usage_analytics_service.calculate_billing_metrics(
            db, org_id, billing_period_start, billing_period_end
        )

        # Get organization details
        from ..models.role import Organization
        org_result = await db.execute(select(Organization).where(Organization.id == org_id))
        org = org_result.scalar_one_or_none()

        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Generate invoice data
        invoice = {
            "invoice_number": f"INV-{org_id}-{billing_period_start.strftime('%Y%m')}",
            "organization": {
                "id": str(org.id),
                "name": org.name,
                "subscription_tier": org.subscription_tier
            },
            "billing_period": {
                "start": billing_period_start.isoformat(),
                "end": billing_period_end.isoformat()
            },
            "usage": billing["usage"],
            "billing": billing["billing"],
            "generated_at": datetime.utcnow().isoformat(),
            "due_date": (billing_period_end + timedelta(days=30)).isoformat()
        }

        return invoice

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate invoice: {str(e)}")


@router.get("/circuit-breakers")
async def get_circuit_breaker_stats(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get circuit breaker statistics"""
    try:
        from ..services.circuit_breaker import circuit_breaker_registry
        return circuit_breaker_registry.get_all_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get circuit breaker stats: {str(e)}")


@router.post("/circuit-breakers/reset")
async def reset_circuit_breakers(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Reset all circuit breakers"""
    try:
        from ..services.circuit_breaker import circuit_breaker_registry
        await circuit_breaker_registry.reset_all()
        return {"message": "All circuit breakers reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset circuit breakers: {str(e)}")


@router.post("/usage/rag")
async def log_rag_usage(
    tokens_used: int,
    confidence: float,
    sources_count: int,
    response_length: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Log RAG query usage for analytics and billing"""
    print(f"[DEBUG] Logging RAG usage for user {current_user.id}: tokens={tokens_used}, confidence={confidence}, sources={sources_count}")
    try:
        from ..services.usage import usage_analytics_service
        await usage_analytics_service.record_rag_usage(
            db,
            user_id=current_user.id,
            tokens_used=tokens_used,
            confidence=confidence,
            sources_count=sources_count,
            response_length=response_length,
            organization_id=current_user.organization_id
        )
        print(f"[DEBUG] RAG usage logged successfully for user {current_user.id}")
        return {"message": "RAG usage logged successfully"}
    except Exception as e:
        print(f"[DEBUG] Failed to log RAG usage for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to log RAG usage: {str(e)}")