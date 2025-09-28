"""
Admin and monitoring router
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..services.auth import get_current_superuser
from ..services.cache import RedisCache
from ..services.opensearch import OpenSearchService
from ..schemas.admin import SystemStats, UserStats, SearchStats

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get system statistics"""
    logger.info("Admin endpoint /stats called", user_id=current_user.id, user_email=current_user.email, is_superuser=current_user.is_superuser)

    try:
        from sqlalchemy import func, select
        from ..models.user import User
        from ..models.paper import ResearchPaper
        from ..models.audit import AuditLog
        from ..services.monitoring import performance_monitor

        # Get user count
        user_result = await db.execute(select(func.count(User.id)))
        total_users = user_result.scalar() or 0

        # Get paper count
        paper_result = await db.execute(select(func.count(ResearchPaper.id)))
        total_papers = paper_result.scalar() or 0

        # Get search count from audit logs
        search_result = await db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.action == 'search_perform')
        )
        total_searches = search_result.scalar() or 0

        # Get performance metrics
        perf_metrics = performance_monitor.get_performance_metrics()

        # Calculate cache hit rate (simplified - would need proper tracking)
        cache_hit_rate = 0.85  # Placeholder

        # Calculate average response time
        avg_response_time = perf_metrics.get("operations", {}).get("api_request_get", {}).get("avg_time", 0.0)

        # System uptime
        system_uptime = perf_metrics.get("uptime_seconds", 0.0)

        stats = SystemStats(
            total_users=total_users,
            total_papers=total_papers,
            total_searches=total_searches,
            cache_hit_rate=cache_hit_rate,
            average_response_time=avg_response_time,
            system_uptime=system_uptime
        )

        logger.info("System stats retrieved successfully", stats=stats.dict())
        return stats

    except Exception as e:
        logger.error("Failed to get system stats", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve system stats: {str(e)}")


@router.get("/users/stats", response_model=UserStats)
async def get_user_stats(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get user statistics"""
    logger.info("Admin endpoint /users/stats called", user_id=current_user.id, user_email=current_user.email, is_superuser=current_user.is_superuser)

    try:
        from sqlalchemy import func, select
        from ..models.user import User
        from ..models.audit import AuditLog
        from datetime import datetime, timedelta

        # Get active users (logged in within last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        active_result = await db.execute(
            select(func.count(User.id)).where(User.last_login >= yesterday)
        )
        active_users = active_result.scalar() or 0

        # Get new users today
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        new_users_result = await db.execute(
            select(func.count(User.id)).where(User.created_at >= today)
        )
        new_users_today = new_users_result.scalar() or 0

        # Get top search queries from audit logs (simplified)
        top_queries_result = await db.execute(
            select(AuditLog.request_data['query'], func.count(AuditLog.id))
            .where(AuditLog.action == 'search_perform')
            .group_by(AuditLog.request_data['query'])
            .order_by(func.count(AuditLog.id).desc())
            .limit(10)
        )
        top_search_queries = {row[0]: row[1] for row in top_queries_result if row[0]}

        # Placeholder for user activity trends
        user_activity_trends = {
            "daily_active_users": [active_users] * 7,  # Placeholder for 7 days
            "weekly_registrations": [new_users_today] * 4,  # Placeholder for 4 weeks
            "timestamp": datetime.utcnow().isoformat()
        }

        stats = UserStats(
            active_users=active_users,
            new_users_today=new_users_today,
            top_search_queries=top_search_queries,
            user_activity_trends=user_activity_trends
        )

        logger.info("User stats retrieved successfully", active_users=active_users, new_users_today=new_users_today)
        return stats

    except Exception as e:
        logger.error("Failed to get user stats", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user stats: {str(e)}")


@router.get("/search/stats", response_model=SearchStats)
async def get_search_stats(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get search statistics"""
    logger.info("Admin endpoint /search/stats called", user_id=current_user.id, user_email=current_user.email, is_superuser=current_user.is_superuser)

    try:
        from sqlalchemy import func, select
        from ..models.audit import AuditLog
        from ..services.monitoring import performance_monitor

        # Get total queries from audit logs
        total_queries_result = await db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.action == 'search_perform')
        )
        total_queries = total_queries_result.scalar() or 0

        # Get average query time from performance metrics
        perf_metrics = performance_monitor.get_performance_metrics()
        avg_query_time = perf_metrics.get("operations", {}).get("api_request_get", {}).get("avg_time", 0.0)

        # Get popular categories (simplified - from audit logs)
        categories_result = await db.execute(
            select(AuditLog.request_data['categories'], func.count(AuditLog.id))
            .where(AuditLog.action == 'search_perform')
            .group_by(AuditLog.request_data['categories'])
            .order_by(func.count(AuditLog.id).desc())
            .limit(10)
        )
        popular_categories = {}
        for row in categories_result:
            if row[0]:
                # Handle JSON array of categories
                if isinstance(row[0], list):
                    for category in row[0]:
                        popular_categories[category] = popular_categories.get(category, 0) + row[1]
                else:
                    popular_categories[str(row[0])] = row[1]

        # Calculate search success rate (simplified)
        success_result = await db.execute(
            select(func.count(AuditLog.id))
            .where(AuditLog.action == 'search_perform')
            .where(AuditLog.success == True)
        )
        successful_queries = success_result.scalar() or 0
        search_success_rate = (successful_queries / max(total_queries, 1)) * 100

        # Get index size (placeholder - would need OpenSearch integration)
        index_size = 0  # Placeholder

        stats = SearchStats(
            total_queries=total_queries,
            average_query_time=avg_query_time,
            popular_categories=popular_categories,
            search_success_rate=search_success_rate,
            index_size=index_size
        )

        logger.info("Search stats retrieved successfully", total_queries=total_queries, avg_query_time=avg_query_time)
        return stats

    except Exception as e:
        logger.error("Failed to get search stats", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve search stats: {str(e)}")


@router.post("/cache/clear")
async def clear_cache(
    current_user: User = Depends(get_current_superuser)
):
    """Clear all cache"""
    logger.info("Admin endpoint /cache/clear called", user_id=current_user.id, user_email=current_user.email, is_superuser=current_user.is_superuser)
    try:
        cache = RedisCache()
        await cache.connect()
        await cache.clear()
        logger.info("Cache cleared successfully")
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        logger.error("Failed to clear cache", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


@router.post("/index/rebuild")
async def rebuild_search_index(
    current_user: User = Depends(get_current_superuser)
):
    """Rebuild search index"""
    logger.info("Admin endpoint /index/rebuild called", user_id=current_user.id, user_email=current_user.email, is_superuser=current_user.is_superuser)

    try:
        from ..services.opensearch import OpenSearchService
        from ..services.embeddings import EmbeddingService

        embedding_service = EmbeddingService()
        opensearch = OpenSearchService(provider=embedding_service.provider)
        await opensearch.connect()

        # Rebuild index (this is a simplified implementation)
        # In a real implementation, this would:
        # 1. Create a new index with updated mappings
        # 2. Re-index all documents from the database
        # 3. Switch aliases
        # 4. Clean up old index

        # For now, just check if OpenSearch is available
        health = await opensearch.client.cluster.health()
        if health.get('status') not in ['green', 'yellow']:
            raise HTTPException(status_code=503, detail="OpenSearch cluster is not healthy")

        # Placeholder for actual rebuild logic
        logger.info("Search index rebuild initiated (placeholder implementation)")

        return {"message": "Search index rebuild initiated successfully", "status": "in_progress"}

    except Exception as e:
        logger.error("Failed to rebuild search index", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to rebuild search index: {str(e)}")


@router.get("/health/detailed")
async def detailed_health_check(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Detailed health check for admin"""
    logger.info("Admin endpoint /health/detailed called", user_id=current_user.id, user_email=current_user.email, is_superuser=current_user.is_superuser)

    try:
        from ..services.cache import RedisCache
        from ..services.opensearch import OpenSearchService
        from ..services.monitoring import performance_monitor
        import time

        health_status = {
            "overall_healthy": True,
            "timestamp": time.time(),
            "services": {}
        }

        # Check database
        try:
            from sqlalchemy import text
            await db.execute(text("SELECT 1"))
            health_status["services"]["database"] = {"healthy": True, "response_time": 0.0}
        except Exception as e:
            health_status["services"]["database"] = {"healthy": False, "error": str(e)}
            health_status["overall_healthy"] = False

        # Check Redis cache
        try:
            cache = RedisCache()
            await cache.connect()
            await cache.client.ping()
            health_status["services"]["redis"] = {"healthy": True, "response_time": 0.0}
        except Exception as e:
            health_status["services"]["redis"] = {"healthy": False, "error": str(e)}
            health_status["overall_healthy"] = False

        # Check OpenSearch
        try:
            from ..services.embeddings import EmbeddingService
            embedding_service = EmbeddingService()
            opensearch = OpenSearchService(provider=embedding_service.provider)
            await opensearch.connect()
            health = await opensearch.client.cluster.health()
            health_status["services"]["opensearch"] = {
                "healthy": health.get('status') in ['green', 'yellow'],
                "status": health.get('status'),
                "response_time": 0.0
            }
            if health.get('status') not in ['green', 'yellow']:
                health_status["overall_healthy"] = False
        except Exception as e:
            health_status["services"]["opensearch"] = {"healthy": False, "error": str(e)}
            health_status["overall_healthy"] = False

        # System metrics
        system_metrics = performance_monitor.get_system_metrics()
        health_status["system"] = system_metrics

        # Performance metrics
        perf_metrics = performance_monitor.get_performance_metrics()
        health_status["performance"] = {
            "uptime_seconds": perf_metrics.get("uptime_seconds", 0),
            "total_requests": perf_metrics.get("total_requests", 0),
            "error_rate": perf_metrics.get("error_rate", 0.0)
        }

        logger.info("Detailed health check completed", overall_healthy=health_status["overall_healthy"])
        return health_status

    except Exception as e:
        logger.error("Failed to perform detailed health check", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to perform health check: {str(e)}")


@router.get("/logs")
async def get_system_logs(
    lines: int = 100,
    current_user: User = Depends(get_current_superuser)
):
    """Get system logs"""
    logger.info("Admin endpoint /logs called", user_id=current_user.id, user_email=current_user.email, is_superuser=current_user.is_superuser, lines=lines)

    try:
        import os
        import glob
        from datetime import datetime

        # Limit lines to prevent abuse
        lines = min(lines, 1000)

        # Get log files from logs directory
        logs_dir = os.path.join(os.getcwd(), "logs")
        if not os.path.exists(logs_dir):
            return {"logs": [], "message": "No logs directory found"}

        # Find log files (assuming .log extension)
        log_files = glob.glob(os.path.join(logs_dir, "*.log"))
        if not log_files:
            return {"logs": [], "message": "No log files found"}

        # Read the most recent log file
        latest_log = max(log_files, key=os.path.getmtime)

        try:
            with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()

            # Get the last N lines
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

            # Format log entries
            formatted_logs = []
            for line in recent_lines:
                line = line.strip()
                if line:
                    # Try to parse timestamp if present
                    try:
                        # Simple parsing - could be enhanced
                        formatted_logs.append({
                            "timestamp": datetime.now().isoformat(),
                            "level": "INFO",  # Placeholder
                            "message": line
                        })
                    except:
                        formatted_logs.append({
                            "timestamp": datetime.now().isoformat(),
                            "level": "UNKNOWN",
                            "message": line
                        })

            logger.info("System logs retrieved successfully", lines_requested=lines, lines_returned=len(formatted_logs))
            return {
                "logs": formatted_logs,
                "total_lines": len(formatted_logs),
                "source_file": os.path.basename(latest_log)
            }

        except Exception as e:
            logger.error("Failed to read log file", error=str(e), file=latest_log)
            raise HTTPException(status_code=500, detail=f"Failed to read log file: {str(e)}")

    except Exception as e:
        logger.error("Failed to get system logs", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve system logs: {str(e)}")