"""
==============================================================================
StaffSync 360 - High-Performance In-Memory & Redis Caching Service
==============================================================================
Provides transparent Redis caching with automatic in-memory fallback for
high-frequency endpoints (analytics summary, center listings).
"""

import json
import logging
import os
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# In-memory LRU/TTL fallback dictionary
_LOCAL_CACHE = {}


class CacheService:
    def __init__(self):
        self.redis_client = None
        self.is_redis_available = False
        self._init_redis()

    def _init_redis(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            import redis
            self.redis_client = redis.from_url(
                redis_url,
                socket_timeout=1.5,
                socket_connect_timeout=1.5,
                decode_responses=True
            )
            # Ping test
            self.redis_client.ping()
            self.is_redis_available = True
            logger.info("Redis cache connected successfully.")
        except Exception as e:
            self.is_redis_available = False
            self.redis_client = None
            logger.debug(f"Redis unavailable, using local memory cache fallback. ({e})")

    def get(self, key: str) -> Optional[Any]:
        """Retrieve item from Redis or local in-memory cache."""
        if self.is_redis_available and self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")

        # Local fallback check
        item = _LOCAL_CACHE.get(key)
        if item:
            val, expiry = item
            if expiry is None or time.time() < expiry:
                return val
            else:
                _LOCAL_CACHE.pop(key, None)
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """Store item in Redis or local in-memory cache with TTL."""
        serialized = json.dumps(value)
        if self.is_redis_available and self.redis_client:
            try:
                self.redis_client.setex(key, ttl_seconds, serialized)
                return True
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")

        # Local fallback store
        expiry = time.time() + ttl_seconds if ttl_seconds else None
        _LOCAL_CACHE[key] = (value, expiry)
        return True

    def delete(self, key: str) -> bool:
        """Delete specific cache key."""
        if self.is_redis_available and self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception:
                pass
        _LOCAL_CACHE.pop(key, None)
        return True

    def invalidate_prefix(self, prefix: str) -> int:
        """Invalidate all keys matching a prefix (e.g. 'analytics:*')."""
        count = 0
        if self.is_redis_available and self.redis_client:
            try:
                keys = self.redis_client.keys(f"{prefix}*")
                if keys:
                    count += self.redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis prefix invalidation failed: {e}")

        # Local fallback flush for matching prefix
        keys_to_remove = [k for k in list(_LOCAL_CACHE.keys()) if k.startswith(prefix)]
        for k in keys_to_remove:
            _LOCAL_CACHE.pop(k, None)
            count += 1
        return count


# Singleton instance
cache = CacheService()
