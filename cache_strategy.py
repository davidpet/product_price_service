"""Cache-related behavior for the app."""

from abc import ABC, abstractmethod

from flask import Flask

from schema import APIRecord

class CacheStrategy(ABC):
    """Abstract base class for caching."""
    @abstractmethod
    def invalidate(self, sku: str):
        """Invalidate the cache for the given sku."""

        raise NotImplementedError
    
    @abstractmethod
    def update(self, sku: str, api_record: APIRecord):
        """Update the cache for the given sku to point to the given record."""

        raise NotImplementedError
    
    @abstractmethod
    def retrieve(self, sku: str) -> APIRecord | None:
        """Retreive the cache entry (or None) for the given sku."""

        raise NotImplementedError
    
    @abstractmethod
    def debug_info(self):
        """Get information for dev testing to watch the cache happening."""

        raise NotImplementedError
    
class InMemoryCacheStrategy(CacheStrategy):
    """Simple in-memory caching for local dev testing."""

    def __init__(self):
        self.cache = {}

    def invalidate(self, sku: str):
        """Invalidate the cache for the given sku."""

        if sku in self.cache:
            del self.cache[sku]
        
    def update(self, sku: str, api_record: APIRecord):
        """Update the cache for the given sku to point to the given record."""

        self.cache[sku] = api_record

    def retrieve(self, sku: str) -> APIRecord | None:
        """Retreive the cache entry (or None) for the given sku."""

        return self.cache.get(sku, None)

    def debug_info(self):
        """Get information for dev testing to watch the cache happening."""

        return self.cache

def get_cache_strategy(app: Flask) -> CacheStrategy:
    """
    Factory function to get a cache strategy based on the environment.

    Args:
        app (Flask): the Flask app to base caching on

    Returns:
        subclass of CacheStrategy to use for caching
    """

    # TODO: take similar options and do similar mirroring to storage strategy
    # TODO: add RedisCacheStrategy
    return InMemoryCacheStrategy()
