"""Unit tests for the LRUCache class."""

import sys
import os
import time
import pytest
from unittest.mock import patch, Mock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from cache import LRUCache


class TestLRUCache:
    """Test suite for LRUCache class."""
    
    def test_init_creates_empty_cache(self):
        """Test that cache initializes as empty."""
        cache = LRUCache(max_size=10, ttl=60)
        assert cache.max_size == 10
        assert cache.ttl == 60
        assert len(cache) == 0
        assert cache.cache == {}
        assert cache.order == []
        
    def test_get_set_basic(self):
        """Test basic set and get operations."""
        cache = LRUCache(max_size=5)
        
        # Set a value
        cache.set("key1", "value1")
        
        # Get the value
        result = cache.get("key1")
        assert result == "value1"
        assert len(cache) == 1
        
    def test_get_missing_returns_none(self):
        """Test that getting a missing key returns None."""
        cache = LRUCache(max_size=5)
        
        # Try to get a non-existent key
        result = cache.get("missing_key")
        assert result is None
        
    def test_max_size_eviction(self):
        """Test that cache evicts least recently used items when full."""
        cache = LRUCache(max_size=3)
        
        # Fill the cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # All items should be present
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        
        # Add a fourth item, should evict key1 (least recently used)
        cache.set("key4", "value4")
        
        # key1 should be evicted
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
        
        # Access key2 to make it recently used
        cache.get("key2")
        
        # Add a fifth item, should evict key3 (now least recently used)
        cache.set("key5", "value5")
        
        assert cache.get("key3") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key4") == "value4"
        assert cache.get("key5") == "value5"
        
    def test_ttl_expiry(self):
        """Test that items expire after TTL."""
        cache = LRUCache(max_size=5, ttl=0.1)  # 100ms TTL
        
        # Set a value
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for TTL to expire
        time.sleep(0.15)
        
        # Value should be expired and return None
        result = cache.get("key1")
        assert result is None
        assert len(cache) == 0  # Expired item should be removed
        
    def test_delete_removes_item(self):
        """Test that delete removes an item from cache."""
        cache = LRUCache(max_size=5)
        
        # Add items
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Delete key1
        cache.delete("key1")
        
        # Verify deletion
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert len(cache) == 1
        
        # Delete non-existent key (should not raise error)
        cache.delete("missing_key")
        
    def test_clear_empties_cache(self):
        """Test that clear removes all items from cache."""
        cache = LRUCache(max_size=5)
        
        # Add items
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Clear cache
        cache.clear()
        
        # Verify cache is empty
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None
        assert len(cache) == 0
        assert cache.cache == {}
        assert cache.order == []
        
    def test_contains_key(self):
        """Test the contains_key method."""
        cache = LRUCache(max_size=5)
        
        # Add an item
        cache.set("key1", "value1")
        
        # Check contains
        assert cache.contains_key("key1") is True
        assert cache.contains_key("missing_key") is False
        
    def test_len_method(self):
        """Test the __len__ method."""
        cache = LRUCache(max_size=5)
        
        assert len(cache) == 0
        
        cache.set("key1", "value1")
        assert len(cache) == 1
        
        cache.set("key2", "value2")
        assert len(cache) == 2
        
        cache.delete("key1")
        assert len(cache) == 1
        
    def test_update_existing_key(self):
        """Test updating an existing key's value."""
        cache = LRUCache(max_size=5)
        
        # Set initial value
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Update the value
        cache.set("key1", "updated_value")
        assert cache.get("key1") == "updated_value"
        assert len(cache) == 1  # Should still have only one item
        
    def test_ttl_refresh_on_access(self):
        """Test that accessing an item refreshes its TTL."""
        cache = LRUCache(max_size=5, ttl=0.2)
        
        # Set a value
        cache.set("key1", "value1")
        
        # Wait half the TTL
        time.sleep(0.1)
        
        # Access the item (should refresh TTL)
        assert cache.get("key1") == "value1"
        
        # Wait another half TTL (item should still be valid due to refresh)
        time.sleep(0.1)
        
        # Item should still be there
        assert cache.get("key1") == "value1"
        
        # Wait full TTL from last access
        time.sleep(0.2)
        
        # Now item should be expired
        assert cache.get("key1") is None
        
    def test_iteration(self):
        """Test that cache can be iterated over."""
        cache = LRUCache(max_size=5)
        
        # Add items
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Test iteration
        items = list(cache)
        assert len(items) == 3
        assert ("key1", "value1") in items
        assert ("key2", "value2") in items
        assert ("key3", "value3") in items
        
    def test_str_representation(self):
        """Test the string representation of cache."""
        cache = LRUCache(max_size=5)
        
        # Empty cache
        assert str(cache) == "LRUCache(max_size=5, ttl=None, size=0)"
        
        # Cache with items
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        expected = "LRUCache(max_size=5, ttl=None, size=2)"
        assert str(cache) == expected


