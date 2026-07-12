"""Tests for the SEO/GEO Framework exception hierarchy."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import pytest
from exceptions import (
    SEOFrameworkError,
    OperationalError,
    ConfigurationError,
    FatalError,
    DataError,
)


class TestSEOFrameworkError:
    """Test the base exception class."""

    def test_basic_creation(self):
        """Base exception should accept a message."""
        err = SEOFrameworkError("something broke")
        assert str(err) == "[SE000] something broke"

    def test_error_code(self):
        """Error code should be set correctly."""
        err = SEOFrameworkError("test", error_code="SE001")
        assert err.error_code == "SE001"

    def test_details(self):
        """Details dict should be stored."""
        err = SEOFrameworkError("test", details={"key": "val"})
        assert err.details == {"key": "val"}

    def test_to_dict(self):
        """to_dict should contain all required keys."""
        err = SEOFrameworkError("msg", error_code="SE999", details={"x": 1})
        d = err.to_dict()
        assert d["error_type"] == "SEOFrameworkError"
        assert d["error_code"] == "SE999"
        assert d["message"] == "msg"
        assert d["details"] == {"x": 1}
        assert "timestamp" in d
        assert d["retryable"] is False

    def test_timestamp(self):
        """Exception should have a UTC timestamp."""
        err = SEOFrameworkError("test")
        assert err.timestamp is not None
        # Should be ISO format
        assert "T" in err.timestamp

    def test_repr(self):
        """repr should include class name and message."""
        err = SEOFrameworkError("broken", error_code="SE001")
        r = repr(err)
        assert "SEOFrameworkError" in r
        assert "broken" in r

    def test_default_not_retryable(self):
        """Base exception should not be retryable by default."""
        err = SEOFrameworkError("test")
        assert err.retryable is False


class TestConfigurationError:
    """Test ConfigurationError specifics."""

    def test_is_operational_error(self):
        """ConfigurationError should inherit from OperationalError."""
        err = ConfigurationError("bad config")
        assert isinstance(err, OperationalError)
        assert isinstance(err, SEOFrameworkError)

    def test_config_key_in_details(self):
        """config_key should be stored in details."""
        err = ConfigurationError("missing key", config_key="API_KEY")
        assert err.details["config_key"] == "API_KEY"

    def test_default_error_code(self):
        """Default error code should be CF001."""
        err = ConfigurationError("test")
        assert err.error_code == "CF001"


class TestFatalError:
    """Test FatalError specifics."""

    def test_not_retryable(self):
        """FatalError should never be retryable."""
        err = FatalError("system down")
        assert err.retryable is False

    def test_recovery_steps(self):
        """Recovery steps should be stored in details."""
        steps = ["restart", "check logs"]
        err = FatalError("crash", recovery_steps=steps)
        assert err.details["recovery_steps"] == steps

    def test_is_operational_error(self):
        """FatalError should inherit from OperationalError."""
        err = FatalError("fatal")
        assert isinstance(err, OperationalError)


class TestDataError:
    """Test DataError specifics."""

    def test_is_framework_error(self):
        """DataError should inherit from SEOFrameworkError."""
        err = DataError("bad data")
        assert isinstance(err, SEOFrameworkError)

    def test_error_code_prefix(self):
        """DataError should use DA prefix."""
        assert DataError.error_code_prefix == "DA"


class TestExceptionChaining:
    """Test that exceptions can be chained with __cause__."""

    def test_chain_with_cause(self):
        """Exceptions should support chaining via raise ... from ..."""
        try:
            try:
                raise ValueError("original")
            except ValueError as ve:
                raise ConfigurationError("wrapper") from ve
        except ConfigurationError as ce:
            assert ce.__cause__ is not None
            assert isinstance(ce.__cause__, ValueError)
