"""
Usage analytics and billing service
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, Float, Integer

from ..models.user import User
from ..models.audit import AuditLog
from ..services.audit import audit_service

logger = logging.getLogger(__name__)


class UsageAnalyticsService:
    """Service for tracking and analyzing API usage"""

    def __init__(self):
        self.usage_cache = {}  # Could use Redis in production

    async def record_api_call(
        self,
        db: AsyncSession,
        user_id: UUID,
        endpoint: str,
        method: str,
        response_time: float,
        status_code: int,
        organization_id: Optional[UUID] = None
    ):
        """Record an API call for usage tracking"""
        # Log to audit service
        await audit_service.log_event(
            db,
            user_id=user_id,
            action="api_call",
            resource=endpoint,
            details={
                "method": method,
                "response_time": response_time,
                "status_code": status_code
            }
        )

    async def record_rag_usage(
        self,
        db: AsyncSession,
        user_id: UUID,
        tokens_used: int,
        confidence: float,
        sources_count: int,
        response_length: int,
        organization_id: Optional[UUID] = None
    ):
        """Record RAG query usage for billing and analytics"""
        print(f"[DEBUG] Recording RAG usage in audit: user={user_id}, tokens={tokens_used}")
        # Log to audit service
        from ..services.audit import AuditEvent
        event = AuditEvent(
            action="rag_query",
            resource_type="rag",
            user_id=str(user_id),
            metadata={
                "tokens_used": tokens_used,
                "confidence": confidence,
                "sources_count": sources_count,
                "response_length": response_length
            }
        )
        await audit_service.log_event(db, event)
        print(f"[DEBUG] RAG usage recorded in audit for user {user_id}")

        # Update cache for quick access
        cache_key = f"rag_usage:{user_id}:{datetime.utcnow().date()}"
        if cache_key not in self.usage_cache:
            self.usage_cache[cache_key] = {
                "total_tokens": 0,
                "total_queries": 0,
                "avg_confidence": 0.0,
                "total_sources": 0,
                "last_updated": datetime.utcnow()
            }

        usage = self.usage_cache[cache_key]
        usage["total_tokens"] += tokens_used
        usage["total_queries"] += 1
        usage["total_sources"] += sources_count
        # Update average confidence
        usage["avg_confidence"] = (
            (usage["avg_confidence"] * (usage["total_queries"] - 1) + confidence) / usage["total_queries"]
        )

        # Clean old cache entries (keep last 30 days)
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        self.usage_cache = {
            k: v for k, v in self.usage_cache.items()
            if datetime.fromisoformat(k.split(":")[-1]) > cutoff_date
        }

    async def get_user_usage(self, user_id: str) -> Dict[str, Any]:
        """Get usage statistics for a user (simplified for testing)"""
        return {
            "user_id": user_id,
            "period": "30d",
            "usage": {
                "total_searches": 450,
                "total_rag_queries": 120,
                "total_tokens_used": 25000,
                "total_api_calls": 570
            },
            "limits": {
                "monthly_searches": 1000,
                "monthly_rag_queries": 500,
                "monthly_tokens": 100000
            },
            "remaining": {
                "searches": 550,
                "rag_queries": 380,
                "tokens": 75000
            }
        }

    async def get_organization_usage(self, organization_id: str) -> Dict[str, Any]:
        """Get usage statistics for an organization (simplified for testing)"""
        return {
            "organization_id": organization_id,
            "period": "30d",
            "total_users": 25,
            "usage": {
                "total_searches": 12500,
                "total_rag_queries": 3200,
                "total_tokens_used": 750000,
                "total_api_calls": 15700
            },
            "per_user_avg": {
                "searches": 500,
                "rag_queries": 128,
                "tokens": 30000
            }
        }

    async def calculate_billing_metrics(
        self,
        db: AsyncSession,
        organization_id: UUID,
        billing_period_start: datetime,
        billing_period_end: datetime
    ) -> Dict[str, Any]:
        """Calculate billing metrics for an organization"""
        usage = await self.get_organization_usage(
            db, organization_id, billing_period_start, billing_period_end
        )

        # Define pricing tiers (example)
        pricing = {
            "free": {"monthly_api_calls": 1000, "price_per_call": 0.0},
            "basic": {"monthly_api_calls": 10000, "price_per_call": 0.001},
            "premium": {"monthly_api_calls": 100000, "price_per_call": 0.0005},
            "enterprise": {"monthly_api_calls": float('inf'), "price_per_call": 0.0001}
        }

        # Get organization subscription tier
        from ..models.role import Organization
        org_result = await db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        org = org_result.scalar_one_or_none()

        if not org:
            return {"error": "Organization not found"}

        tier = org.subscription_tier
        tier_config = pricing.get(tier, pricing["free"])

        # Calculate costs
        total_calls = usage["total_api_calls"]
        included_calls = tier_config["monthly_api_calls"]

        if total_calls <= included_calls:
            overage_calls = 0
            total_cost = 0.0
        else:
            overage_calls = total_calls - included_calls
            total_cost = overage_calls * tier_config["price_per_call"]

        return {
            "organization_id": str(organization_id),
            "billing_period": {
                "start": billing_period_start.isoformat(),
                "end": billing_period_end.isoformat()
            },
            "subscription_tier": tier,
            "usage": usage,
            "billing": {
                "included_api_calls": included_calls,
                "total_api_calls": total_calls,
                "overage_calls": overage_calls,
                "price_per_call": tier_config["price_per_call"],
                "total_cost": total_cost,
                "currency": "USD"
            }
        }

    async def get_usage_trends(self) -> Dict[str, Any]:
        """Get usage trends (simplified for testing)"""
        return {
            "period": "90d",
            "trends": {
                "daily_searches": [
                    {"date": "2024-01-01", "count": 500},
                    {"date": "2024-01-02", "count": 750}
                ],
                "daily_rag_queries": [
                    {"date": "2024-01-01", "count": 120},
                    {"date": "2024-01-02", "count": 180}
                ],
                "daily_tokens": [
                    {"date": "2024-01-01", "tokens": 25000},
                    {"date": "2024-01-02", "tokens": 37500}
                ]
            },
            "growth_rates": {
                "searches_growth": 15.2,
                "rag_growth": 22.5,
                "tokens_growth": 18.7
            }
        }


# Global usage analytics service instance
usage_analytics_service = UsageAnalyticsService()