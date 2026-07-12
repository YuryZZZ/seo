"""Tests for SEOGEOConfig validation and convenience functions.

Note: The project has both src/config.py (legacy module) and src/config/ (package).
The package wraps the legacy module. We import from src.config.py directly via
the legacy loader to test the actual dataclasses.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import pytest
from unittest.mock import patch
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_config_module():
    """Load src/config.py directly (not the config/ package)."""
    config_path = Path(__file__).resolve().parents[1] / "src" / "config.py"
    spec = spec_from_file_location("_test_config_module", config_path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Load the module once for the test session
_cfg = _load_config_module()


class TestAPIConfig:
    """Test APIConfig dataclass."""

    def test_defaults_are_none(self):
        """All API keys should default to None when env vars are not set."""
        with patch.dict(os.environ, {}, clear=True):
            cfg = _cfg.APIConfig()
            assert cfg.google_api_key is None
            assert cfg.openai_api_key is None
            assert cfg.anthropic_api_key is None

    def test_loads_from_env(self):
        """API keys should be loaded from environment variables."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key-123"}, clear=True):
            cfg = _cfg.APIConfig()
            assert cfg.google_api_key == "test-key-123"

    def test_explicit_value_overrides_env(self):
        """Explicitly passed values should take precedence over env vars."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "env-key"}, clear=True):
            cfg = _cfg.APIConfig(google_api_key="explicit-key")
            assert cfg.google_api_key == "explicit-key"


class TestRetryConfig:
    """Test RetryConfig defaults."""

    def test_defaults(self):
        """RetryConfig should have sensible defaults."""
        cfg = _cfg.RetryConfig()
        assert cfg.max_retries == 3
        assert cfg.base_delay == 1.0
        assert cfg.jitter is True
        assert 429 in cfg.retry_status_codes
        assert 503 in cfg.retry_status_codes


class TestContentConfig:
    """Test ContentConfig defaults."""

    def test_word_count_range(self):
        """Content config should have valid word count range."""
        cfg = _cfg.ContentConfig()
        assert cfg.min_word_count < cfg.max_word_count
        assert cfg.min_word_count >= 500

    def test_keyword_density_range(self):
        """Keyword density should be between 0 and 0.1."""
        cfg = _cfg.ContentConfig()
        assert 0 < cfg.min_keyword_density < 0.1
        assert cfg.min_keyword_density < cfg.max_keyword_density


class TestSEOGEOConfig:
    """Test the main SEOGEOConfig class."""

    def test_creation(self):
        """SEOGEOConfig should be creatable with all defaults."""
        cfg = _cfg.SEOGEOConfig()
        assert cfg.api is not None
        assert cfg.retry is not None
        assert cfg.content is not None

    def test_validate_returns_issues_list(self):
        """validate() should return a list."""
        cfg = _cfg.SEOGEOConfig()
        issues = cfg.validate()
        assert isinstance(issues, list)

    def test_validate_flags_missing_api_key(self):
        """validate() should flag missing GOOGLE_API_KEY."""
        with patch.dict(os.environ, {}, clear=True):
            cfg = _cfg.SEOGEOConfig()
            issues = cfg.validate()
            assert any("GOOGLE_API_KEY" in i for i in issues)

    def test_from_env(self):
        """from_env() should return a valid config."""
        cfg = _cfg.SEOGEOConfig.from_env()
        assert cfg is not None

    def test_output_dir_created(self):
        """SEOGEOConfig should create output_dir."""
        cfg = _cfg.SEOGEOConfig()
        assert cfg.output_dir is not None
        assert cfg.cache_dir is not None


class TestGetApiKey:
    """Test the get_api_key convenience function."""

    def test_returns_none_for_unknown(self):
        """get_api_key should return None for unknown services."""
        # Reset global state
        _cfg._config = None
        result = _cfg.get_api_key("nonexistent_service")
        assert result is None
        _cfg._config = None

    def test_returns_key_for_known_service(self):
        """get_api_key should return the key for known services."""
        _cfg._config = None
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True):
            result = _cfg.get_api_key("openai")
            assert result == "sk-test"
        _cfg._config = None

    def test_case_insensitive(self):
        """get_api_key should be case-insensitive."""
        _cfg._config = None
        # Just verify it doesn't crash on different cases
        _cfg.get_api_key("Google")
        _cfg.get_api_key("OPENAI")
        _cfg.get_api_key("anthropic")
        _cfg._config = None
