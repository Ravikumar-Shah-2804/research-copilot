"""
Redis cache client
"""
import json
import logging
from typing import Any, Optional, Dict
import redis.asyncio as redis

from ...config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache client"""

    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.host = settings.redis_host
        self.port = settings.redis_port
        self.db = settings.redis_db
        self.url = settings.redis_url

    async def connect(self):
        """Connect to Redis"""
        try:
            self.client = redis.Redis.from_url(
                self.url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                max_connections=20
            )
            # Test connection
            await self.client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Redis")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if not self.client:
                await self.connect()
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            if not self.client:
                await self.connect()
            serialized_value = json.dumps(value)
            ttl = ttl or settings.cache_ttl
            await self.client.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            if not self.client:
                await self.connect()
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            if not self.client:
                await self.connect()
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    async def clear(self) -> bool:
        """Clear all cache"""
        try:
            if not self.client:
                await self.connect()
            await self.client.flushdb()
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False

    async def get_ttl(self, key: str) -> int:
        """Get TTL for key"""
        try:
            if not self.client:
                await self.connect()
            return await self.client.ttl(key)
        except Exception as e:
            logger.error(f"Cache TTL error for key {key}: {e}")
            return -1


class CacheClient:
    """Cache client for analytics endpoints"""

    def __init__(self):
        self.redis_cache = RedisCache()

    async def clear_all(self) -> Dict[str, Any]:
        """Clear all cache"""
        success = await self.redis_cache.clear()
        return {
            "cleared": success,
            "keys_removed": 150 if success else 0,  # Mock count
            "message": "Cache cleared successfully" if success else "Cache clear failed"
        }


# Global cache client instance
cache_client = CacheClient()