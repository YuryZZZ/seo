"""Shared test fixtures for SEO/GEO Framework test suite."""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
root_dir = Path(__file__).parent.parent
src_dir = root_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def mock_cache_manager():
    """Mock CacheManager fixture for tests that need isolated cache."""
    from src.cache import CacheManager, MemoryCache
    return CacheManager(backend=MemoryCache())


@pytest.fixture
def mock_llm_response():
    """Mock LLM response fixture."""
    return "This is a mock LLM-generated response for testing purposes."


@pytest.fixture
def sample_config():
    """Sample SEOGEOConfig for testing."""
    from src.config import SEOGEOConfig
    return SEOGEOConfig()


@pytest.fixture
def sample_keyword_data():
    """Sample keyword research data for testing."""
    return {
        "primary_keyword": "seo optimization",
        "secondary_keywords": ["search engine optimization", "seo tools", "organic traffic"],
        "long_tail_keywords": ["how to improve seo ranking", "best seo practices 2025"],
        "search_volume": {"seo optimization": 12000, "seo tools": 8500},
    }


@pytest.fixture
def sample_content_brief():
    """Sample content brief for testing content generation."""
    return {
        "topic": "SEO Best Practices",
        "target_keyword": "seo optimization",
        "content_type": "blog_post",
        "word_count": 2500,
        "tone": "professional",
        "audience": "marketing professionals",
    }


@pytest.fixture
def sample_article_html():
    """Sample HTML article for testing parsers and analyzers."""
    return """
    <article>
        <h1>SEO Best Practices for 2025</h1>
        <p>Search engine optimization is critical for online visibility.</p>
        <h2>Why is SEO Important?</h2>
        <p>SEO drives organic traffic to your website. Studies show that 68% of online
        experiences begin with a search engine.</p>
        <h2>On-Page SEO Techniques</h2>
        <p>Optimize your title tags, meta descriptions, and header structure.</p>
        <h3>Title Tags</h3>
        <p>Keep title tags under 60 characters for optimal display.</p>
        <h2>Technical SEO Checklist</h2>
        <p>Ensure fast page load times, mobile responsiveness, and proper indexing.</p>
    </article>
    """
