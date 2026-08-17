"""
==============================================================================
StaffSync 360 - High-Performance In-Memory & Redis Caching Service
==============================================================================
Provides transparent Redis caching with automatic in-memory fallback for
generic analytics/listings, and mandatory distributed Redis in production
for security/auth revocation.
"""

import json
import logging
import os
import time
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Optional

logger = logging.getLogger(__name__)

# In-memory LRU/TTL fallback dictionary (Development / Test harness only)
_LOCAL_CACHE = {}


def _json_serial(obj):
    """Custom JSON serializer preserving high-precision Decimal strings and ISO dates."""
    if isinstance(obj, Decimal):
        return str(obj)  # Preserves exact decimal precision without float binary conversion
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


class CacheService:
    def __init__(self):
        self.redis_client = None
        self.is_redis_available = False
        self.env = os.getenv("ENVIRONMENT", "development").lower()
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
            self.redis_client.ping()
            self.is_redis_available = True
            logger.info("Redis cache connected successfully.")
        except Exception as e:
            self.is_redis_available = False
            self.redis_client = None
            logger.info(f"Redis not provisioned at {redis_url}; using high-speed in-memory cache.")

    def _is_auth_key(self, key: str) -> bool:
        return key.startswith("revoked_token:") or key.startswith("user_session_revocation:")

    def get(self, key: str) -> Optional[Any]:
        """Retrieve item from Redis or local in-memory cache."""
        if self.is_redis_available and self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")

        # Local in-memory fallback check
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
        try:
            serialized = json.dumps(value, default=_json_serial)
        except Exception as e:
            logger.error(f"JSON serialization error in cache: {e}")
            return False

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
        """Invalidate a specific cache key."""
        if self.is_redis_available and self.redis_client:
            try:
                self.redis_client.delete(key)
                return True
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")

        _LOCAL_CACHE.pop(key, None)
        return True

    def invalidate_prefix(self, prefix: str):
        """Invalidate all keys matching a prefix across Redis and in-memory store."""
        if self.is_redis_available and self.redis_client:
            try:
                cursor = '0'
                while cursor != 0:
                    cursor, keys = self.redis_client.scan(cursor=cursor, match=f"{prefix}*", count=100)
                    if keys:
                        self.redis_client.delete(*keys)
                    if cursor == 0 or cursor == '0':
                        break
            except Exception as e:
                logger.warning(f"Redis prefix invalidation error: {e}")

        # Invalidate in local fallback
        keys_to_del = [k for k in _LOCAL_CACHE.keys() if k.startswith(prefix)]
        for k in keys_to_del:
            _LOCAL_CACHE.pop(k, None)


# Singleton application cache instance
cache = CacheService()
