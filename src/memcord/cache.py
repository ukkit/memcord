"""Advanced multi-level caching system for memcord performance optimization.

This module implements:
1. Memory cache (LRU) for frequently accessed slots
2. Disk cache for search results and computed data
3. Cache invalidation strategies
4. Usage pattern analysis for predictive loading
5. Performance monitoring and statistics
"""

import asyncio
import hashlib
import json
import time
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import aiofiles
import aiofiles.os
from dataclasses import dataclass, asdict
from enum import Enum

from .models import MemorySlot, SearchResult, SearchQuery


class CacheLevel(Enum):
    """Cache level enumeration."""
    MEMORY = "memory"
    DISK = "disk"


class EvictionPolicy(Enum):
    """Cache eviction policy enumeration."""
    LRU = "lru"
    LFU = "lfu"
    TTL = "ttl"


@dataclass
class CacheEntry:
    """Represents a cached entry with metadata."""
    key: str
    value: Any
    timestamp: datetime
    access_count: int = 0
    last_accessed: datetime = None
    size_bytes: int = 0
    ttl_seconds: Optional[int] = None
    
    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = self.timestamp
        if self.size_bytes == 0:
            self.size_bytes = self._calculate_size()
    
    def _calculate_size(self) -> int:
        """Calculate approximate size of cached value in bytes."""
        try:
            if isinstance(self.value, str):
                return len(self.value.encode('utf-8'))
            elif isinstance(self.value, (dict, list)):
                return len(json.dumps(self.value).encode('utf-8'))
            elif hasattr(self.value, '__dict__'):
                return len(json.dumps(asdict(self.value)).encode('utf-8'))
            else:
                return len(str(self.value).encode('utf-8'))
        except Exception:
            return 1024  # Default size if calculation fails
    
    def is_expired(self) -> bool:
        """Check if entry has expired based on TTL."""
        if self.ttl_seconds is None:
            return False
        return datetime.now() > self.timestamp + timedelta(seconds=self.ttl_seconds)
    
    def touch(self):
        """Update access metadata."""
        self.access_count += 1
        self.last_accessed = datetime.now()


@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0
    hit_rate: float = 0.0
    avg_access_time_ms: float = 0.0
    
    def update_hit_rate(self):
        """Update hit rate calculation."""
        total = self.hits + self.misses
        self.hit_rate = self.hits / total if total > 0 else 0.0


class LRUCache:
    """Thread-safe LRU cache implementation."""
    
    def __init__(self, max_size: int = 1000, max_memory_bytes: int = 100 * 1024 * 1024):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_bytes
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self._stats = CacheStats()
    
    async def get(self, key: str) -> Tuple[Optional[Any], bool]:
        """Get value from cache. Returns (value, hit_flag)."""
        start_time = time.time()
        
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                
                # Check if entry is expired
                if entry.is_expired():
                    del self._cache[key]
                    self._stats.misses += 1
                    self._stats.evictions += 1
                    self._update_stats()
                    return None, False
                
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                entry.touch()
                
                self._stats.hits += 1
                access_time = (time.time() - start_time) * 1000
                self._update_access_time(access_time)
                self._update_stats()
                
                return entry.value, True
            
            self._stats.misses += 1
            self._update_stats()
            return None, False
    
    async def put(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Put value in cache. Returns success status."""
        async with self._lock:
            now = datetime.now()
            entry = CacheEntry(
                key=key,
                value=value,
                timestamp=now,
                ttl_seconds=ttl_seconds
            )
            
            # Remove existing entry if present
            if key in self._cache:
                old_entry = self._cache[key]
                self._stats.size_bytes -= old_entry.size_bytes
                del self._cache[key]
            
            # Check memory constraints
            if self._stats.size_bytes + entry.size_bytes > self.max_memory_bytes:
                await self._evict_by_memory()
            
            # Check size constraints
            if len(self._cache) >= self.max_size:
                await self._evict_by_size()
            
            # Add new entry
            self._cache[key] = entry
            self._stats.size_bytes += entry.size_bytes
            self._stats.entry_count = len(self._cache)
            
            return True
    
    async def remove(self, key: str) -> bool:
        """Remove entry from cache."""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                self._stats.size_bytes -= entry.size_bytes
                del self._cache[key]
                self._stats.entry_count = len(self._cache)
                return True
            return False
    
    async def clear(self):
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._stats = CacheStats()
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count of removed entries."""
        removed_count = 0
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() 
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                entry = self._cache[key]
                self._stats.size_bytes -= entry.size_bytes
                del self._cache[key]
                removed_count += 1
                self._stats.evictions += 1
            
            self._stats.entry_count = len(self._cache)
        
        return removed_count
    
    async def _evict_by_memory(self):
        """Evict entries to free memory."""
        target_size = int(self.max_memory_bytes * 0.8)  # Evict to 80% capacity
        
        while self._stats.size_bytes > target_size and self._cache:
            # Remove least recently used entry
            key, entry = self._cache.popitem(last=False)
            self._stats.size_bytes -= entry.size_bytes
            self._stats.evictions += 1
    
    async def _evict_by_size(self):
        """Evict entries to maintain size limit."""
        while len(self._cache) >= self.max_size:
            # Remove least recently used entry
            key, entry = self._cache.popitem(last=False)
            self._stats.size_bytes -= entry.size_bytes
            self._stats.evictions += 1
    
    def _update_access_time(self, access_time_ms: float):
        """Update average access time."""
        if self._stats.avg_access_time_ms == 0:
            self._stats.avg_access_time_ms = access_time_ms
        else:
            # Exponential moving average
            self._stats.avg_access_time_ms = (
                0.9 * self._stats.avg_access_time_ms + 0.1 * access_time_ms
            )
    
    def _update_stats(self):
        """Update cache statistics."""
        self._stats.entry_count = len(self._cache)
        self._stats.update_hit_rate()
    
    def get_stats(self) -> CacheStats:
        """Get current cache statistics."""
        return self._stats


class DiskCache:
    """Persistent disk-based cache for search results and computed data."""
    
    def __init__(self, cache_dir: str = "cache", max_files: int = 10000):
        self.cache_dir = Path(cache_dir)
        self.max_files = max_files
        self.cache_dir.mkdir(exist_ok=True)
        self._lock = asyncio.Lock()
        self._stats = CacheStats()
        self._index_file = self.cache_dir / "cache_index.json"
        self._index: Dict[str, Dict[str, Any]] = {}
        self._index_dirty = False
        
    async def initialize(self):
        """Initialize disk cache by loading index."""
        try:
            if self._index_file.exists():
                async with aiofiles.open(self._index_file, 'r') as f:
                    content = await f.read()
                    self._index = json.loads(content)
        except Exception as e:
            print(f"Warning: Failed to load cache index: {e}")
            self._index = {}
    
    async def get(self, key: str) -> Tuple[Optional[Any], bool]:
        """Get value from disk cache."""
        start_time = time.time()
        cache_key = self._get_cache_key(key)
        
        async with self._lock:
            if cache_key not in self._index:
                self._stats.misses += 1
                self._update_stats()
                return None, False
            
            entry_info = self._index[cache_key]
            cache_file = self.cache_dir / f"{cache_key}.json"
            
            try:
                # Check if file exists and is not expired
                if not cache_file.exists():
                    del self._index[cache_key]
                    await self._save_index()
                    self._stats.misses += 1
                    self._update_stats()
                    return None, False
                
                # Check TTL
                created_at = datetime.fromisoformat(entry_info['created_at'])
                ttl = entry_info.get('ttl_seconds')
                if ttl and datetime.now() > created_at + timedelta(seconds=ttl):
                    await aiofiles.os.remove(str(cache_file))
                    del self._index[cache_key]
                    await self._save_index()
                    self._stats.misses += 1
                    self._stats.evictions += 1
                    self._update_stats()
                    return None, False
                
                # Load cached value
                async with aiofiles.open(cache_file, 'r') as f:
                    content = await f.read()
                    data = json.loads(content)
                
                # Update access metadata
                self._index[cache_key]['access_count'] += 1
                self._index[cache_key]['last_accessed'] = datetime.now().isoformat()
                self._index_dirty = True
                # Note: Index saving is batched for performance - will be saved during cleanup
                
                self._stats.hits += 1
                access_time = (time.time() - start_time) * 1000
                self._update_access_time(access_time)
                self._update_stats()
                
                return data['value'], True
                
            except Exception as e:
                print(f"Warning: Failed to load cached value for {key}: {e}")
                # Clean up corrupted cache entry
                if cache_file.exists():
                    await aiofiles.os.remove(str(cache_file))
                if cache_key in self._index:
                    del self._index[cache_key]
                    await self._save_index()
                
                self._stats.misses += 1
                self._update_stats()
                return None, False
    
    async def put(self, key: str, value: Any, ttl_seconds: Optional[int] = 3600) -> bool:
        """Put value in disk cache."""
        cache_key = self._get_cache_key(key)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        async with self._lock:
            try:
                # Prepare cache data
                cache_data = {
                    'key': key,
                    'value': value,
                    'created_at': datetime.now().isoformat()
                }
                
                # Write to cache file
                async with aiofiles.open(cache_file, 'w') as f:
                    await f.write(json.dumps(cache_data, default=str, ensure_ascii=False))
                
                # Update index
                file_size = cache_file.stat().st_size if cache_file.exists() else 0
                self._index[cache_key] = {
                    'key': key,
                    'created_at': datetime.now().isoformat(),
                    'last_accessed': datetime.now().isoformat(),
                    'access_count': 0,
                    'size_bytes': file_size,
                    'ttl_seconds': ttl_seconds
                }
                self._index_dirty = True

                # Check file count limit
                if len(self._index) > self.max_files:
                    await self._evict_old_entries()
                else:
                    # For put operations, save immediately to ensure consistency
                    await self._save_index()
                self._update_stats()
                return True
                
            except Exception as e:
                print(f"Warning: Failed to cache value for {key}: {e}")
                return False
    
    async def remove(self, key: str) -> bool:
        """Remove entry from disk cache."""
        cache_key = self._get_cache_key(key)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        async with self._lock:
            try:
                if cache_file.exists():
                    await aiofiles.os.remove(str(cache_file))
                
                if cache_key in self._index:
                    del self._index[cache_key]
                    await self._save_index()
                
                return True
            except Exception as e:
                print(f"Warning: Failed to remove cached value for {key}: {e}")
                return False
    
    async def clear(self):
        """Clear all disk cache entries."""
        async with self._lock:
            try:
                # Remove all cache files
                for cache_file in self.cache_dir.glob("*.json"):
                    if cache_file.name != "cache_index.json":
                        await aiofiles.os.remove(str(cache_file))
                
                # Clear index
                self._index = {}
                await self._save_index()
                self._stats = CacheStats()
                
            except Exception as e:
                print(f"Warning: Failed to clear disk cache: {e}")
    
    async def cleanup_expired(self) -> int:
        """Remove expired cache entries."""
        removed_count = 0
        async with self._lock:
            expired_keys = []
            now = datetime.now()
            
            for cache_key, entry_info in self._index.items():
                ttl = entry_info.get('ttl_seconds')
                if ttl:
                    created_at = datetime.fromisoformat(entry_info['created_at'])
                    if now > created_at + timedelta(seconds=ttl):
                        expired_keys.append(cache_key)
            
            for cache_key in expired_keys:
                cache_file = self.cache_dir / f"{cache_key}.json"
                try:
                    if cache_file.exists():
                        await aiofiles.os.remove(str(cache_file))
                    del self._index[cache_key]
                    removed_count += 1
                    self._stats.evictions += 1
                except Exception:
                    pass
            
            if removed_count > 0:
                await self._save_index()
            else:
                # Save index if dirty even if no expired entries
                await self._save_index_if_dirty()
            
        return removed_count
    
    def _get_cache_key(self, key: str) -> str:
        """Generate cache key from input key."""
        return hashlib.md5(key.encode('utf-8')).hexdigest()
    
    async def _save_index(self):
        """Save cache index to disk."""
        try:
            async with aiofiles.open(self._index_file, 'w') as f:
                await f.write(json.dumps(self._index, indent=2))
            self._index_dirty = False
        except Exception as e:
            print(f"Warning: Failed to save cache index: {e}")

    async def _save_index_if_dirty(self):
        """Save cache index to disk only if it has been modified."""
        if self._index_dirty:
            await self._save_index()
    
    async def _evict_old_entries(self):
        """Evict old cache entries to maintain file limit."""
        target_count = int(self.max_files * 0.8)  # Evict to 80% capacity
        
        # Sort by last accessed time (oldest first)
        sorted_entries = sorted(
            self._index.items(),
            key=lambda x: x[1]['last_accessed']
        )
        
        entries_to_remove = len(sorted_entries) - target_count
        for i in range(entries_to_remove):
            cache_key, _ = sorted_entries[i]
            cache_file = self.cache_dir / f"{cache_key}.json"
            
            try:
                if cache_file.exists():
                    await aiofiles.os.remove(str(cache_file))
                del self._index[cache_key]
                self._stats.evictions += 1
            except Exception:
                pass
    
    def _update_access_time(self, access_time_ms: float):
        """Update average access time."""
        if self._stats.avg_access_time_ms == 0:
            self._stats.avg_access_time_ms = access_time_ms
        else:
            self._stats.avg_access_time_ms = (
                0.9 * self._stats.avg_access_time_ms + 0.1 * access_time_ms
            )
    
    def _update_stats(self):
        """Update cache statistics."""
        self._stats.entry_count = len(self._index)
        self._stats.size_bytes = sum(entry.get('size_bytes', 0) for entry in self._index.values())
        self._stats.update_hit_rate()
    
    def get_stats(self) -> CacheStats:
        """Get current cache statistics."""
        return self._stats


class UsagePatternAnalyzer:
    """Analyzes access patterns for predictive caching."""
    
    def __init__(self, history_size: int = 10000):
        self.history_size = history_size
        self._access_history: List[Tuple[str, datetime]] = []
        self._access_patterns: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'frequency': 0,
            'last_access': None,
            'access_times': [],
            'co_accessed_with': defaultdict(int),
            'temporal_patterns': defaultdict(int)  # hour of day -> count
        })
        self._lock = asyncio.Lock()
    
    async def record_access(self, key: str):
        """Record an access event for pattern analysis."""
        now = datetime.now()
        async with self._lock:
            # Record in history
            self._access_history.append((key, now))
            
            # Trim history if too large
            if len(self._access_history) > self.history_size:
                self._access_history = self._access_history[-self.history_size:]
            
            # Update patterns
            pattern = self._access_patterns[key]
            pattern['frequency'] += 1
            pattern['last_access'] = now
            pattern['access_times'].append(now)
            
            # Track temporal patterns (hour of day)
            pattern['temporal_patterns'][now.hour] += 1
            
            # Track co-access patterns (items accessed together)
            recent_keys = {
                k for k, t in self._access_history[-10:] 
                if (now - t).total_seconds() < 300  # Within 5 minutes
            }
            for other_key in recent_keys:
                if other_key != key:
                    pattern['co_accessed_with'][other_key] += 1
    
    async def get_prefetch_candidates(self, current_key: str, limit: int = 5) -> List[str]:
        """Get keys that should be prefetched based on current access."""
        async with self._lock:
            candidates = []
            
            if current_key in self._access_patterns:
                pattern = self._access_patterns[current_key]
                
                # Get items frequently co-accessed with current key
                co_accessed = sorted(
                    pattern['co_accessed_with'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:limit]
                
                candidates.extend([key for key, _ in co_accessed])
            
            return candidates[:limit]
    
    async def get_warming_candidates(self, limit: int = 10) -> List[Tuple[str, float]]:
        """Get keys that should be warmed based on usage patterns."""
        now = datetime.now()
        current_hour = now.hour
        
        async with self._lock:
            candidates = []
            
            for key, pattern in self._access_patterns.items():
                # Calculate score based on multiple factors
                score = 0.0
                
                # Frequency score
                frequency_score = min(1.0, pattern['frequency'] / 100)
                score += frequency_score * 0.4
                
                # Temporal score (likely to be accessed at current hour)
                temporal_score = pattern['temporal_patterns'].get(current_hour, 0)
                max_temporal = max(pattern['temporal_patterns'].values()) if pattern['temporal_patterns'] else 1
                temporal_score = temporal_score / max_temporal
                score += temporal_score * 0.3
                
                # Recency score (recently accessed items are more likely to be accessed again)
                if pattern['last_access']:
                    hours_since = (now - pattern['last_access']).total_seconds() / 3600
                    recency_score = max(0, 1 - hours_since / 24)  # Decay over 24 hours
                    score += recency_score * 0.3
                
                if score > 0.1:  # Minimum threshold
                    candidates.append((key, score))
            
            # Sort by score and return top candidates
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[:limit]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get usage pattern statistics."""
        async with self._lock:
            return {
                'total_accesses': len(self._access_history),
                'unique_keys': len(self._access_patterns),
                'average_frequency': sum(p['frequency'] for p in self._access_patterns.values()) / max(1, len(self._access_patterns)),
                'most_accessed': sorted(
                    [(k, p['frequency']) for k, p in self._access_patterns.items()],
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            }


class CacheManager:
    """Unified cache manager coordinating memory and disk caches."""
    
    def __init__(
        self, 
        memory_cache_size: int = 1000,
        memory_cache_memory_mb: int = 100,
        disk_cache_dir: str = "cache",
        disk_cache_max_files: int = 10000,
        enable_predictive_loading: bool = True
    ):
        self.memory_cache = LRUCache(
            max_size=memory_cache_size,
            max_memory_bytes=memory_cache_memory_mb * 1024 * 1024
        )
        self.disk_cache = DiskCache(
            cache_dir=disk_cache_dir,
            max_files=disk_cache_max_files
        )
        self.usage_analyzer = UsagePatternAnalyzer() if enable_predictive_loading else None
        self.enable_predictive_loading = enable_predictive_loading
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._warming_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def initialize(self):
        """Initialize the cache manager."""
        await self.disk_cache.initialize()
        
        # Start background tasks
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        if self.enable_predictive_loading:
            self._warming_task = asyncio.create_task(self._warming_loop())
    
    async def shutdown(self):
        """Shutdown the cache manager."""
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._warming_task:
            self._warming_task.cancel()
    
    async def get(self, key: str, cache_level: CacheLevel = CacheLevel.MEMORY) -> Tuple[Optional[Any], bool]:
        """Get value from cache with fallback strategy."""
        # Record access pattern
        if self.usage_analyzer:
            await self.usage_analyzer.record_access(key)
        
        # Try memory cache first
        if cache_level == CacheLevel.MEMORY:
            value, hit = await self.memory_cache.get(key)
            if hit:
                return value, True
            
            # Try disk cache as fallback
            value, hit = await self.disk_cache.get(key)
            if hit:
                # Promote to memory cache
                await self.memory_cache.put(key, value)
                return value, True
        
        # Try disk cache only
        elif cache_level == CacheLevel.DISK:
            return await self.disk_cache.get(key)
        
        return None, False
    
    async def put(
        self, 
        key: str, 
        value: Any, 
        cache_level: CacheLevel = CacheLevel.MEMORY,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """Put value in cache."""
        if cache_level == CacheLevel.MEMORY:
            success = await self.memory_cache.put(key, value, ttl_seconds)
            
            # Also cache in disk for persistence
            await self.disk_cache.put(key, value, ttl_seconds or 3600)
            
            return success
        
        elif cache_level == CacheLevel.DISK:
            return await self.disk_cache.put(key, value, ttl_seconds)
        
        return False
    
    async def remove(self, key: str):
        """Remove key from all cache levels."""
        await self.memory_cache.remove(key)
        await self.disk_cache.remove(key)
    
    async def clear(self):
        """Clear all caches."""
        await self.memory_cache.clear()
        await self.disk_cache.clear()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        memory_stats = self.memory_cache.get_stats()
        disk_stats = self.disk_cache.get_stats()
        
        stats = {
            'memory_cache': {
                'hits': memory_stats.hits,
                'misses': memory_stats.misses,
                'hit_rate': memory_stats.hit_rate,
                'entries': memory_stats.entry_count,
                'size_mb': memory_stats.size_bytes / (1024 * 1024),
                'avg_access_time_ms': memory_stats.avg_access_time_ms,
                'evictions': memory_stats.evictions
            },
            'disk_cache': {
                'hits': disk_stats.hits,
                'misses': disk_stats.misses,
                'hit_rate': disk_stats.hit_rate,
                'entries': disk_stats.entry_count,
                'size_mb': disk_stats.size_bytes / (1024 * 1024),
                'avg_access_time_ms': disk_stats.avg_access_time_ms,
                'evictions': disk_stats.evictions
            },
            'combined': {
                'total_hits': memory_stats.hits + disk_stats.hits,
                'total_misses': memory_stats.misses + disk_stats.misses,
                'overall_hit_rate': (memory_stats.hits + disk_stats.hits) / max(1, memory_stats.hits + disk_stats.hits + memory_stats.misses + disk_stats.misses),
                'total_entries': memory_stats.entry_count + disk_stats.entry_count,
                'total_size_mb': (memory_stats.size_bytes + disk_stats.size_bytes) / (1024 * 1024)
            }
        }
        
        if self.usage_analyzer:
            stats['usage_patterns'] = await self.usage_analyzer.get_stats()
        
        return stats
    
    async def _cleanup_loop(self):
        """Background task for cache cleanup."""
        while self._running:
            try:
                # Cleanup expired entries every 5 minutes
                await asyncio.sleep(300)
                
                memory_cleaned = await self.memory_cache.cleanup_expired()
                disk_cleaned = await self.disk_cache.cleanup_expired()
                
                if memory_cleaned > 0 or disk_cleaned > 0:
                    print(f"Cache cleanup: removed {memory_cleaned} memory entries, {disk_cleaned} disk entries")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Warning: Cache cleanup error: {e}")
    
    async def _warming_loop(self):
        """Background task for cache warming based on usage patterns."""
        if not self.usage_analyzer:
            return
        
        while self._running:
            try:
                # Warm cache every 30 minutes
                await asyncio.sleep(1800)
                
                candidates = await self.usage_analyzer.get_warming_candidates(limit=10)
                
                for key, score in candidates:
                    # Check if already cached
                    _, hit = await self.memory_cache.get(key)
                    if not hit:
                        # Try to warm from disk cache or trigger loading
                        value, disk_hit = await self.disk_cache.get(key)
                        if disk_hit:
                            await self.memory_cache.put(key, value)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Warning: Cache warming error: {e}")


# Cache key generators for different data types
def generate_slot_cache_key(slot_name: str) -> str:
    """Generate cache key for memory slot."""
    return f"slot:{slot_name}"


def generate_search_cache_key(query: SearchQuery) -> str:
    """Generate cache key for search query."""
    query_data = {
        'query': query.query,
        'case_sensitive': query.case_sensitive,
        'include_tags': sorted(query.include_tags) if query.include_tags else None,
        'exclude_tags': sorted(query.exclude_tags) if query.exclude_tags else None,
        'include_groups': sorted(query.include_groups) if query.include_groups else None,
        'exclude_groups': sorted(query.exclude_groups) if query.exclude_groups else None,
        'content_types': sorted(query.content_types) if query.content_types else None,
        'max_results': query.max_results
    }
    
    # Create deterministic hash
    query_str = json.dumps(query_data, sort_keys=True)
    return f"search:{hashlib.md5(query_str.encode('utf-8')).hexdigest()}"


def generate_stats_cache_key(stats_type: str, identifier: Optional[str] = None) -> str:
    """Generate cache key for statistics."""
    if identifier:
        return f"stats:{stats_type}:{identifier}"
    return f"stats:{stats_type}"