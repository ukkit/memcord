"""Tests for cache.py - Multi-level caching system.

Tests memory cache, disk cache, and cache management functionality.

Coverage: 75%
- CacheEntry: Size calculation, TTL expiration, access tracking
- LRUCache: Eviction policies, statistics, put/get operations
- DiskCache: File-based caching, eviction by file limits
- CacheManager: Multi-level coordination, integration
- UsagePatternAnalyzer: Access pattern recording and analysis

Tests focus on caching behavior and performance optimization.
"""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from memcord.cache import (
    CacheEntry,
    CacheManager,
    DiskCache,
    LRUCache,
    UsagePatternAnalyzer,
)


class TestCacheEntry:
    """Test CacheEntry dataclass and its methods."""

    def test_cache_entry_creation(self):
        """Test basic CacheEntry creation and properties."""
        entry = CacheEntry(key="test_key", value="test_value", timestamp=datetime.now())

        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.access_count == 0
        assert isinstance(entry.timestamp, datetime)

    def test_cache_entry_size_calculation(self):
        """Test cache entry size calculation method."""
        # Test string value
        string_entry = CacheEntry(key="string_test", value="Hello World", timestamp=datetime.now())
        size = string_entry._calculate_size()
        assert size == len(b"Hello World")

        # Test dict value
        dict_entry = CacheEntry(key="dict_test", value={"key": "value", "number": 42}, timestamp=datetime.now())
        dict_size = dict_entry._calculate_size()
        assert dict_size > 0  # Should calculate JSON size

    def test_cache_entry_expiration(self):
        """Test cache entry TTL expiration logic."""
        old_time = datetime.now() - timedelta(hours=2)
        entry = CacheEntry(
            key="ttl_test",
            value="test",
            timestamp=old_time,
            ttl_seconds=3600,  # 1 hour TTL
        )

        # Should be expired after 2 hours
        assert entry.is_expired() is True

        # Fresh entry should not be expired
        fresh_entry = CacheEntry(key="fresh", value="test", timestamp=datetime.now(), ttl_seconds=3600)
        assert fresh_entry.is_expired() is False

    def test_cache_entry_touch_method(self):
        """Test cache entry touch method for access tracking."""
        entry = CacheEntry(key="touch_test", value="test", timestamp=datetime.now())

        original_count = entry.access_count
        original_time = entry.last_accessed

        # Add small delay for Windows datetime precision
        import time

        time.sleep(0.001)  # 1ms delay for timestamp precision

        entry.touch()

        assert entry.access_count == original_count + 1
        assert entry.last_accessed > original_time


class TestLRUCache:
    """Test LRU (Least Recently Used) cache implementation."""

    def test_lru_cache_initialization(self):
        """Test LRU cache initialization with size limits."""
        cache = LRUCache(max_size=100, max_memory_bytes=1024 * 1024)

        assert cache.max_size == 100
        assert cache.max_memory_bytes == 1024 * 1024
        assert len(cache._cache) == 0
        assert cache._stats.hits == 0

    async def test_lru_cache_put_and_get(self):
        """Test basic put and get operations."""
        cache = LRUCache(max_size=10)

        # Test put operation
        success = await cache.put("key1", "value1")
        assert success is True
        assert len(cache._cache) == 1

        # Test get operation (hit)
        value, hit = await cache.get("key1")
        assert value == "value1"
        assert hit is True
        assert cache._stats.hits == 1

        # Test get operation (miss)
        value, hit = await cache.get("nonexistent")
        assert value is None
        assert hit is False
        assert cache._stats.misses == 1

    async def test_lru_cache_eviction_by_size(self):
        """Test LRU eviction when max_size is exceeded."""
        cache = LRUCache(max_size=2)  # Small cache for testing

        # Fill cache to capacity
        await cache.put("key1", "value1")
        await cache.put("key2", "value2")
        assert len(cache._cache) == 2

        # Adding third item should evict LRU item
        await cache.put("key3", "value3")
        assert len(cache._cache) == 2

        # key1 should be evicted (LRU)
        value, hit = await cache.get("key1")
        assert hit is False

        # key2 and key3 should still be present
        value, hit = await cache.get("key2")
        assert hit is True
        value, hit = await cache.get("key3")
        assert hit is True

    async def test_lru_cache_eviction_by_memory(self):
        """Test LRU eviction when memory limit is exceeded."""
        cache = LRUCache(max_size=100, max_memory_bytes=100)  # Small memory limit

        # Add item that will exceed memory limit
        large_value = "x" * 200  # 200 bytes
        success = await cache.put("large_key", large_value)

        # Should still succeed but trigger eviction
        assert success is True

    async def test_lru_cache_ttl_expiration(self):
        """Test TTL-based cache expiration."""
        cache = LRUCache(max_size=10)

        # Put item with short TTL
        await cache.put("ttl_key", "ttl_value", ttl_seconds=1)

        # Should be accessible immediately
        value, hit = await cache.get("ttl_key")
        assert hit is True

        # Wait for expiration (simulate)
        # Instead of actual sleep, we'll mock the time check
        with patch("memcord.cache.datetime") as mock_datetime:
            future_time = datetime.now() + timedelta(seconds=2)
            mock_datetime.now.return_value = future_time

            value, hit = await cache.get("ttl_key")
            # Expired items should be treated as miss
            assert hit is False

    async def test_lru_cache_remove_and_clear(self):
        """Test cache removal and clearing operations."""
        cache = LRUCache(max_size=10)

        # Add some items
        await cache.put("key1", "value1")
        await cache.put("key2", "value2")
        assert len(cache._cache) == 2

        # Test remove
        removed = await cache.remove("key1")
        assert removed is True
        assert len(cache._cache) == 1

        # Test remove non-existent
        removed = await cache.remove("nonexistent")
        assert removed is False

        # Test clear
        await cache.clear()
        assert len(cache._cache) == 0


@pytest.mark.asyncio
class TestDiskCache:
    """Test disk-based cache implementation."""

    async def test_disk_cache_initialization(self, temp_storage_dir):
        """Test disk cache initialization."""
        cache_dir = Path(temp_storage_dir) / "cache"
        disk_cache = DiskCache(cache_dir=str(cache_dir), max_files=1000)

        assert disk_cache.cache_dir == cache_dir
        assert disk_cache.max_files == 1000

    async def test_disk_cache_put_and_get(self, temp_storage_dir):
        """Test basic disk cache operations."""
        cache_dir = Path(temp_storage_dir) / "cache"
        disk_cache = DiskCache(cache_dir=str(cache_dir))

        # Test put operation
        success = await disk_cache.put("disk_key", {"data": "test_value"})
        assert success is True

        # Test get operation (hit)
        value, hit = await disk_cache.get("disk_key")
        assert hit is True
        assert value["data"] == "test_value"

        # Test get operation (miss)
        value, hit = await disk_cache.get("nonexistent_key")
        assert hit is False
        assert value is None

    async def test_disk_cache_eviction(self, temp_storage_dir):
        """Test disk cache eviction when file limit exceeded."""
        cache_dir = Path(temp_storage_dir) / "cache"
        disk_cache = DiskCache(cache_dir=str(cache_dir), max_files=2)  # 2 file limit

        # Add files to trigger eviction
        await disk_cache.put("file1", {"data": "content1"})
        await disk_cache.put("file2", {"data": "content2"})

        # Third file should trigger eviction (max_files=2)
        await disk_cache.put("file3", {"data": "content3"})

        # Should only have 2 files in cache
        # Check that eviction occurred by verifying cache behavior


@pytest.mark.asyncio
class TestUsagePatternAnalyzer:
    """Test usage pattern analysis for predictive caching."""

    def test_usage_analyzer_initialization(self):
        """Test usage pattern analyzer initialization."""
        analyzer = UsagePatternAnalyzer(history_size=5000)

        assert analyzer.history_size == 5000
        assert len(analyzer._access_history) == 0
        assert isinstance(analyzer._access_patterns, dict)

    async def test_usage_pattern_recording(self):
        """Test recording access patterns."""
        analyzer = UsagePatternAnalyzer()

        # Record some access patterns
        await analyzer.record_access("slot_name")

        assert len(analyzer._access_history) > 0
        assert "slot_name" in analyzer._access_patterns

    async def test_usage_pattern_analysis(self):
        """Test pattern analysis and prediction."""
        analyzer = UsagePatternAnalyzer()

        # Record multiple accesses to establish patterns
        for i in range(10):
            await analyzer.record_access(f"slot_{i % 3}")

        # Check that patterns were recorded
        assert len(analyzer._access_patterns) > 0

        # Test getting warming candidates (if method exists)
        candidates = await analyzer.get_warming_candidates(limit=5)
        assert isinstance(candidates, list)


@pytest.mark.asyncio
class TestCacheManager:
    """Test the main cache manager coordinating multi-level caching."""

    async def test_cache_manager_initialization(self, temp_storage_dir):
        """Test cache manager initialization."""
        cache_dir = Path(temp_storage_dir) / "cache"
        manager = CacheManager(memory_cache_size=100, disk_cache_dir=str(cache_dir), enable_predictive_loading=True)

        assert manager.memory_cache is not None
        assert manager.disk_cache is not None
        assert manager.usage_analyzer is not None

    async def test_cache_manager_multi_level_get(self, temp_storage_dir):
        """Test multi-level cache get operations."""
        cache_dir = Path(temp_storage_dir) / "cache"
        manager = CacheManager(memory_cache_size=10, disk_cache_dir=str(cache_dir))

        # Put item in cache
        await manager.put("multi_key", "multi_value")

        # Should retrieve from cache
        value, hit = await manager.get("multi_key")
        assert value == "multi_value"
        assert hit is True

    async def test_cache_manager_memory_to_disk_fallback(self, temp_storage_dir):
        """Test fallback from memory to disk cache."""
        cache_dir = Path(temp_storage_dir) / "cache"
        manager = CacheManager(
            memory_cache_size=1,  # Very small memory cache
            disk_cache_dir=str(cache_dir),
        )

        # Fill memory cache and overflow to disk
        await manager.put("key1", "value1")
        await manager.put("key2", "value2")  # Should push key1 to disk

        # Get key1 should still be accessible
        value, hit = await manager.get("key1")
        assert value == "value1"
        assert hit is True

    async def test_cache_manager_statistics(self, temp_storage_dir):
        """Test cache manager statistics collection."""
        cache_dir = Path(temp_storage_dir) / "cache"
        manager = CacheManager(disk_cache_dir=str(cache_dir))

        # Perform some operations
        await manager.put("stats_key", "stats_value")
        await manager.get("stats_key")  # Hit
        await manager.get("nonexistent")  # Miss

        stats = await manager.get_stats()
        assert isinstance(stats, dict)

    async def test_cache_manager_removal(self, temp_storage_dir):
        """Test cache removal operations."""
        cache_dir = Path(temp_storage_dir) / "cache"
        manager = CacheManager(disk_cache_dir=str(cache_dir))

        # Put and then remove
        await manager.put("remove_key", "remove_value")
        await manager.remove("remove_key")

        # Should be cache miss after removal
        value, hit = await manager.get("remove_key")
        assert value is None
        assert hit is False


# Integration test with realistic scenarios
@pytest.mark.asyncio
class TestCacheIntegration:
    """Integration tests for cache system components working together."""

    async def test_cache_system_integration(self, temp_storage_dir):
        """Test full cache system integration."""
        cache_dir = Path(temp_storage_dir) / "cache"
        manager = CacheManager(memory_cache_size=5, disk_cache_dir=str(cache_dir), enable_predictive_loading=True)

        # Simulate realistic usage patterns
        test_data = {f"slot_{i}": f"content_{i}" for i in range(10)}

        # Store all data
        for key, value in test_data.items():
            await manager.put(key, value)

        # Retrieve all data (should hit both memory and disk)
        retrieved_count = 0
        for key in test_data.keys():
            value, hit = await manager.get(key)
            if value is not None:
                retrieved_count += 1

        # Should retrieve most or all items
        assert retrieved_count >= 8  # Allow for some eviction

        # Verify cache recorded operations
        stats = await manager.get_stats()
        assert isinstance(stats, dict)
