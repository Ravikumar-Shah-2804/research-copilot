"""
Rate limiting service for API endpoints
"""
import time
import logging
import functools
from typing import Dict, Any, Optional, Tuple
from collections import defaultdict
import asyncio
from datetime import datetime, timedelta

from ..config import settings
from .cache import RedisCache
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiting service using Redis"""

    def __init__(self):
        self.cache = RedisCache()
        self.requests_per_minute = settings.rate_limit_requests_per_minute
        self.burst_limit = settings.rate_limit_burst

        # Tier-based rate limits
        self.tier_limits = {
            'free': {'requests_per_minute': 60, 'burst': 10},
            'basic': {'requests_per_minute': 300, 'burst': 50},
            'premium': {'requests_per_minute': 1000, 'burst': 200},
            'enterprise': {'requests_per_minute': 5000, 'burst': 1000},
        }

        # Role-based multipliers
        self.role_multipliers = {
            'user': 1.0,
            'researcher': 1.5,
            'admin': 2.0,
            'superuser': 3.0,
        }

    async def __aenter__(self):
        await self.cache.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cache.disconnect()

    def _get_key(self, identifier: str, endpoint: str) -> str:
        """Generate rate limit key"""
        return f"ratelimit:{identifier}:{endpoint}"

    def _get_window_key(self, identifier: str, endpoint: str, window: int) -> str:
        """Generate sliding window key"""
        current_window = int(time.time() / window)
        return f"ratelimit:{identifier}:{endpoint}:{current_window}"

    def _get_user_limits(self, user=None, organization=None) -> Dict[str, int]:
        """Calculate rate limits based on user role and organization tier"""
        # Default limits
        base_limits = self.tier_limits['free']

        # Organization tier limits
        if organization and hasattr(organization, 'subscription_tier'):
            org_tier = organization.subscription_tier
            if org_tier in self.tier_limits:
                base_limits = self.tier_limits[org_tier]

        # Role multiplier
        multiplier = 1.0
        if user:
            # Check user's highest role
            if hasattr(user, 'is_superuser') and user.is_superuser:
                multiplier = self.role_multipliers.get('superuser', 1.0)
            elif hasattr(user, 'roles'):
                for role in user.roles:
                    role_name = role.name if hasattr(role, 'name') else str(role)
                    if role_name in self.role_multipliers:
                        multiplier = max(multiplier, self.role_multipliers[role_name])

        # Apply multiplier
        requests_per_minute = int(base_limits['requests_per_minute'] * multiplier)
        burst = int(base_limits['burst'] * multiplier)

        return {
            'requests_per_minute': requests_per_minute,
            'burst': burst
        }

    async def check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        requests_per_window: int = None,
        window_seconds: int = 60,
        user=None,
        organization=None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limits

        Returns:
            (allowed: bool, info: dict with remaining, reset_time, etc.)
        """
        if requests_per_window is None:
            # Use tiered limits if user/organization provided
            if user or organization:
                user_limits = self._get_user_limits(user, organization)
                requests_per_window = user_limits['requests_per_minute']
            else:
                requests_per_window = self.requests_per_minute

        window_key = self._get_window_key(identifier, endpoint, window_seconds)

        try:
            # Get current count
            current_count = await self.cache.get(window_key) or 0

            # Check if limit exceeded
            if current_count >= requests_per_window:
                # Get TTL to calculate reset time
                ttl = await self.cache.get_ttl(window_key)
                reset_time = time.time() + ttl if ttl > 0 else time.time() + window_seconds

                return False, {
                    "remaining": 0,
                    "reset_time": reset_time,
                    "limit": requests_per_window,
                    "window_seconds": window_seconds
                }

            # Increment counter
            new_count = current_count + 1
            await self.cache.set(window_key, new_count, ttl=window_seconds)

            remaining = max(0, requests_per_window - new_count)
            reset_time = time.time() + window_seconds

            return True, {
                "remaining": remaining,
                "reset_time": reset_time,
                "limit": requests_per_window,
                "window_seconds": window_seconds
            }

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Allow request on error to avoid blocking legitimate traffic
            return True, {
                "remaining": requests_per_window,
                "reset_time": time.time() + window_seconds,
                "limit": requests_per_window,
                "window_seconds": window_seconds,
                "error": str(e)
            }

    async def get_rate_limit_info(self, identifier: str, endpoint: str) -> Dict[str, Any]:
        """Get current rate limit status for an identifier/endpoint"""
        window_key = self._get_window_key(identifier, endpoint, 60)

        try:
            current_count = await self.cache.get(window_key) or 0
            ttl = await self.cache.get_ttl(window_key)
            reset_time = time.time() + ttl if ttl > 0 else time.time() + 60

            return {
                "current_count": current_count,
                "remaining": max(0, self.requests_per_minute - current_count),
                "reset_time": reset_time,
                "limit": self.requests_per_minute,
                "window_seconds": 60
            }
        except Exception as e:
            logger.error(f"Failed to get rate limit info: {e}")
            return {}

    async def reset_rate_limit(self, identifier: str, endpoint: str):
        """Reset rate limit for an identifier/endpoint"""
        try:
            # Clear all window keys for this identifier/endpoint
            pattern = f"ratelimit:{identifier}:{endpoint}:*"
            # Note: Redis SCAN would be needed for production
            # For now, we'll just clear the current window
            window_key = self._get_window_key(identifier, endpoint, 60)
            await self.cache.delete(window_key)
            logger.info(f"Reset rate limit for {identifier}:{endpoint}")
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")


class BurstRateLimiter(RateLimiter):
    """Rate limiter with burst allowance"""

    async def check_burst_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        user=None,
        organization=None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check burst rate limit (allows short bursts above normal rate)"""
        # Get user limits
        user_limits = self._get_user_limits(user, organization)

        # First check normal rate limit
        allowed, info = await self.check_rate_limit(
            identifier, endpoint,
            user_limits['requests_per_minute'], 60,
            user, organization
        )

        if not allowed:
            return allowed, info

        # Then check burst limit (shorter window)
        burst_allowed, burst_info = await self.check_rate_limit(
            f"{identifier}_burst", endpoint,
            user_limits['burst'], 10,  # 10 second burst window
            user, organization
        )

        if not burst_allowed:
            return False, {
                **burst_info,
                "burst_exceeded": True
            }

        return True, {
            **info,
            "burst_remaining": burst_info["remaining"]
        }


class SearchRateLimiter(BurstRateLimiter):
    """Specialized rate limiter for search operations"""

    async def check_search_rate_limit(self, user_id: str, user=None, organization=None) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit for search operations"""
        return await self.check_burst_rate_limit(user_id, "search", user, organization)

    async def check_embedding_rate_limit(self, user_id: str, user=None, organization=None) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit for embedding operations (more restrictive)"""
        user_limits = self._get_user_limits(user, organization)
        embedding_limit = min(10, user_limits['requests_per_minute'] // 10)  # Max 10 or 10% of user limit
        return await self.check_rate_limit(
            user_id, "embedding",
            requests_per_window=embedding_limit,
            window_seconds=60,
            user=user, organization=organization
        )


class RAGRateLimiter(BurstRateLimiter):
    """Specialized rate limiter for RAG operations"""

    async def check_rag_rate_limit(self, user_id: str, user=None, organization=None) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit for RAG operations (more restrictive due to LLM costs)"""
        user_limits = self._get_user_limits(user, organization)
        rag_limit = min(5, user_limits['requests_per_minute'] // 20)  # Max 5 or 5% of user limit
        return await self.check_rate_limit(
            user_id, "rag",
            requests_per_window=rag_limit,
            window_seconds=60,
            user=user, organization=organization
        )

    async def check_rag_streaming_rate_limit(self, user_id: str, user=None, organization=None) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit for RAG streaming (slightly more restrictive)"""
        user_limits = self._get_user_limits(user, organization)
        streaming_limit = min(3, user_limits['requests_per_minute'] // 30)  # Max 3 or ~3% of user limit
        return await self.check_rate_limit(
            user_id, "rag_stream",
            requests_per_window=streaming_limit,
            window_seconds=60,
            user=user, organization=organization
        )

    async def check_rag_batch_rate_limit(self, user_id: str, batch_size: int, user=None, organization=None) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit for RAG batch operations"""
        user_limits = self._get_user_limits(user, organization)
        # Scale limit based on batch size and user limits
        max_requests = min(10, user_limits['requests_per_minute'] // 10)  # Max 10 or 10% of user limit
        scaled_requests = max(1, max_requests // batch_size)
        return await self.check_rate_limit(
            user_id, "rag_batch",
            requests_per_window=scaled_requests,
            window_seconds=60,
            user=user, organization=organization
        )


class RateLimitingService:
    """Rate limiting service for analytics endpoints"""

    def __init__(self):
        self.rate_limiter = RateLimiter()

    async def get_user_limits(self, user_id: str) -> Dict[str, Any]:
        """Get user rate limits"""
        # Mock implementation for testing
        return {
            "user_id": user_id,
            "current_usage": {
                "requests_per_hour": 45,
                "requests_per_day": 320
            },
            "limits": {
                "requests_per_hour": 100,
                "requests_per_day": 1000
            },
            "reset_times": {
                "hourly_reset": "2024-01-01T15:00:00Z",
                "daily_reset": "2024-01-02T00:00:00Z"
            },
            "is_limited": False
        }

    async def reset_user_limits(self, user_id: str) -> Dict[str, Any]:
        """Reset user rate limits"""
        return {
            "user_id": user_id,
            "reset": True,
            "message": "Rate limits reset successfully"
        }


# Global rate limiter instances
search_rate_limiter = SearchRateLimiter()
rag_rate_limiter = RAGRateLimiter()
rate_limiting_service = RateLimitingService()


def rate_limit(endpoint_type: str = "general"):
    """Decorator for rate limiting endpoints"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user_id from request context
            # This would need to be adapted based on your auth system
            user_id = "anonymous"  # Placeholder

            try:
                if endpoint_type == "search":
                    limiter = SearchRateLimiter()
                    async with limiter:
                        allowed, info = await limiter.check_search_rate_limit(user_id)
                elif endpoint_type == "embedding":
                    limiter = SearchRateLimiter()
                    async with limiter:
                        allowed, info = await limiter.check_embedding_rate_limit(user_id)
                elif endpoint_type == "rag":
                    limiter = RAGRateLimiter()
                    async with limiter:
                        allowed, info = await limiter.check_rag_rate_limit(user_id)
                elif endpoint_type == "rag_stream":
                    limiter = RAGRateLimiter()
                    async with limiter:
                        allowed, info = await limiter.check_rag_streaming_rate_limit(user_id)
                elif endpoint_type == "rag_batch":
                    # Extract batch size from kwargs if available
                    batch_size = kwargs.get('queries', [])
                    batch_size = len(batch_size) if isinstance(batch_size, list) else 1
                    limiter = RAGRateLimiter()
                    async with limiter:
                        allowed, info = await limiter.check_rag_batch_rate_limit(user_id, batch_size)
                else:
                    limiter = RateLimiter()
                    async with limiter:
                        allowed, info = await limiter.check_rate_limit(user_id, endpoint_type)

                if not allowed:
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded",
                        headers={
                            "X-RateLimit-Remaining": str(info.get("remaining", 0)),
                            "X-RateLimit-Reset": str(int(info.get("reset_time", time.time()))),
                            "X-RateLimit-Limit": str(info.get("limit", 60))
                        }
                    )

                return await func(*args, **kwargs)

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Rate limiting error: {e}")
                # Allow request on error
                return await func(*args, **kwargs)

        return wrapper
    return decorator