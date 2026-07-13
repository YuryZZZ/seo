"""Caching layer for SEO/GEO Framework."""
import time
import json
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CacheBackend:
    """Abstract base class for cache backends."""
    def get(self, key: str) -> Any:
        raise NotImplementedError
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        raise NotImplementedError
    
    def delete(self, key: str) -> bool:
        raise NotImplementedError
    
    def clear(self) -> None:
        raise NotImplementedError


class MemoryCache(CacheBackend):
    """In-memory cache backend with hit/miss tracking."""
    def __init__(self):
        self._cache: Dict[str, tuple] = {}
        self._hits: int = 0
        self._misses: int = 0
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            self._misses += 1
            return None
        value, expires_at = self._cache[key]
        if datetime.now() > expires_at:
            del self._cache[key]
            self._misses += 1
            return None
        self._hits += 1
        return value
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        expires_at = datetime.now() + timedelta(seconds=ttl)
        self._cache[key] = (value, expires_at)
    
    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> None:
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared: {count} items")


class RedisCache(CacheBackend):
    """Redis cache backend with hit/miss tracking and JSON serialization."""
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, password: Optional[str] = None):
        try:
            import redis
        except ImportError:
            raise ImportError("redis package is required for RedisCache. Install with 'pip install redis'")
            
        self._redis = redis.Redis(host=host, port=port, db=db, password=password, decode_responses=True)
        self._hits = 0
        self._misses = 0

    def _serialize(self, value: Any) -> str:
        """Serialize complex objects to JSON."""
        return json.dumps(value)

    def _deserialize(self, value: str) -> Any:
        """Deserialize JSON strings to objects."""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    def get(self, key: str) -> Optional[Any]:
        try:
            value = self._redis.get(key)
            if value is None:
                self._misses += 1
                return None
            self._hits += 1
            return self._deserialize(value)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            self._misses += 1
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        try:
            serialized_value = self._serialize(value)
            self._redis.setex(key, ttl, serialized_value)
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    def delete(self, key: str) -> bool:
        try:
            return bool(self._redis.delete(key))
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    def clear(self) -> None:
        try:
            self._redis.flushdb()
            logger.info("Redis cache cleared")
        except Exception as e:
            logger.error(f"Redis clear error: {e}")

class CacheManager:
    """High-level cache manager."""
    def __init__(self, backend: Optional[CacheBackend] = None):
        self.backend = backend or MemoryCache()
    
    def get(self, key: str) -> Optional[Any]:
        cache_key = self._make_key(key)
        return self.backend.get(cache_key)
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        cache_key = self._make_key(key)
        self.backend.set(cache_key, value, ttl)
    
    def delete(self, key: str) -> bool:
        cache_key = self._make_key(key)
        return self.backend.delete(cache_key)
    
    def clear(self) -> None:
        self.backend.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Return cache statistics for monitoring."""
        result = {"backend": type(self.backend).__name__}
        if isinstance(self.backend, MemoryCache) or isinstance(self.backend, RedisCache):
            result.update({
                "hits": self.backend._hits,
                "misses": self.backend._misses,
                "hit_rate": round(
                    self.backend._hits / max(1, self.backend._hits + self.backend._misses), 3
                ),
            })
            if isinstance(self.backend, MemoryCache):
                result["entries"] = len(self.backend._cache)
        return result
    
    def _make_key(self, key: str) -> str:
        return f"seo_geo:{key}"


# Global cache instance
cache = CacheManager()


class LRUCache:
    def __init__(self, max_size: int = 100, ttl: Optional[float] = None):
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Any] = {}
        self.order: List[str] = []
        self._timestamps: Dict[str, float] = {}

    def __len__(self) -> int:
        self._check_ttl()
        return len(self.cache)

    def __iter__(self):
        self._check_ttl()
        for k in list(self.order):
            if k in self.cache:
                yield k, self.cache[k]

    def __str__(self) -> str:
        return f"LRUCache(max_size={self.max_size}, ttl={self.ttl}, size={len(self)})"

    def _check_ttl(self) -> None:
        if self.ttl is None:
            return
        now = time.time()
        expired = [k for k, t in self._timestamps.items() if now - t > self.ttl]
        for k in expired:
            self._evict(k)

    def _evict(self, key: str) -> None:
        if key in self.cache:
            del self.cache[key]
        if key in self.order:
            self.order.remove(key)
        if key in self._timestamps:
            del self._timestamps[key]

    def get(self, key: str) -> Optional[Any]:
        self._check_ttl()
        if key not in self.cache:
            return None
        # Refresh order
        self.order.remove(key)
        self.order.append(key)
        if self.ttl is not None:
            self._timestamps[key] = time.time()
        return self.cache[key]

    def set(self, key: str, value: Any) -> None:
        self._check_ttl()
        if key in self.cache:
            self._evict(key)
        elif len(self.cache) >= self.max_size and self.order:
            lru = self.order[0]
            self._evict(lru)

        self.cache[key] = value
        self.order.append(key)
        self._timestamps[key] = time.time()

    def delete(self, key: str) -> bool:
        if key in self.cache:
            self._evict(key)
            return True
        return False

    def clear(self) -> None:
        self.cache.clear()
        self.order.clear()
        self._timestamps.clear()

    def contains_key(self, key: str) -> bool:
        self._check_ttl()
        return key in self.cache


__all__ = ['CacheBackend', 'MemoryCache', 'RedisCache', 'CacheManager', 'cache', 'LRUCache']
