import time
import hashlib
from typing import Dict, Any, Optional

class SimpleCache:
    """
    Simple in-memory cache for API responses to avoid repeated calls.
    """
    
    def __init__(self, ttl_seconds=300):  # 5 minutes default TTL
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds
    
    def _generate_key(self, query: str, source: str) -> str:
        """Generate cache key from query and source."""
        return hashlib.md5(f"{query}_{source}".encode()).hexdigest()
    
    def get(self, query: str, source: str) -> Optional[Any]:
        """Get cached data if still valid."""
        key = self._generate_key(query, source)
        
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry['timestamp'] < self.ttl_seconds:
                return entry['data']
            else:
                # Remove expired entry
                del self.cache[key]
        
        return None
    
    def set(self, query: str, source: str, data: Any) -> None:
        """Cache data with timestamp."""
        key = self._generate_key(query, source)
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def clear(self) -> None:
        """Clear all cached data."""
        self.cache.clear()
    
    def cleanup_expired(self) -> None:
        """Remove expired entries."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time - entry['timestamp'] >= self.ttl_seconds
        ]
        for key in expired_keys:
            del self.cache[key]

# Global cache instance
api_cache = SimpleCache(ttl_seconds=300)  # 5 minutes cache
