"""SEO/GEO Framework - 10-agent orchestration system for content optimization."""

__version__ = "1.1.0"

# Lazy imports - import when needed to avoid circular dependencies
# Core agents are imported directly from their modules when used

# Utilities - import from submodules
try:
    from src.utils import (
        slugify,
        truncate_text,
        extract_keywords,
        calculate_readability,
        merge_dicts,
        flatten_dict,
        hash_content,
    )
except ImportError:
    pass  # Utilities may not be fully configured yet

# Logging - use correct function names
try:
    from src.logging_config import configure_logging, get_logger
    setup_logging = configure_logging  # Alias for compatibility
except ImportError:
    def get_logger(name):
        import logging
        return logging.getLogger(name)
    def setup_logging(**kwargs):
        pass

# Cache and rate limiter
try:
    from src.cache import CacheManager, MemoryCache
    from src.rate_limiter import RateLimiter
except ImportError:
    CacheManager = None
    MemoryCache = None
    RateLimiter = None

__all__ = [
    # Core
    "SEOGEOOrchestrator",
    "IAArchitect",
    "MasterCopywriter",
    "SchemaEngineer",
    "MediaStudio",
    "GEOResearcher",
    # Utilities
    "slugify",
    "truncate_text",
    "extract_keywords",
    "calculate_readability",
    "merge_dicts",
    "flatten_dict",
    "hash_content",
    "setup_logging",
    "get_logger",
    "CacheManager",
    "MemoryCache",
    "RateLimiter",
]
