"""Tests for the health server endpoints."""

import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import pytest
from unittest.mock import patch, MagicMock
from http.server import HTTPServer
from io import BytesIO


class MockRequest:
    """Mock HTTP request for testing handler without a real socket."""
    def __init__(self, path):
        self.path = path


class MockWfile(BytesIO):
    """Writable buffer that captures response body."""
    pass


def make_handler(path):
    """Create a HealthCheckHandler for the given path without a real server."""
    from health_server import HealthCheckHandler

    class TestableHandler(HealthCheckHandler):
        def __init__(self, path):
            self.path = path
            self.headers_sent = {}
            self.response_code = None
            self.wfile = MockWfile()
            self._response_body = None

        def send_response(self, code):
            self.response_code = code

        def send_header(self, key, value):
            self.headers_sent[key] = value

        def end_headers(self):
            pass

    handler = TestableHandler(path)
    return handler


class TestHealthEndpoint:
    """Test the /health endpoint."""

    def test_health_returns_200(self):
        """Health endpoint should always return 200."""
        handler = make_handler("/health")
        handler.do_GET()
        assert handler.response_code == 200

    def test_health_returns_json(self):
        """Health endpoint should return valid JSON with expected fields."""
        handler = make_handler("/health")
        handler.do_GET()
        body = json.loads(handler.wfile.getvalue())
        assert body["status"] == "healthy"
        assert body["service"] == "seo-geo-framework"
        assert body["version"] == "2.1"
        assert "uptime_seconds" in body
        assert "timestamp" in body

    def test_health_has_no_cache_header(self):
        """Health endpoint should have Cache-Control: no-cache."""
        handler = make_handler("/health")
        handler.do_GET()
        assert handler.headers_sent.get("Cache-Control") == "no-cache, no-store"


class TestReadyEndpoint:
    """Test the /ready endpoint."""

    def test_ready_returns_checks(self):
        """Ready endpoint should return check statuses."""
        handler = make_handler("/ready")
        handler.do_GET()
        body = json.loads(handler.wfile.getvalue())
        assert "checks" in body
        assert "python" in body["checks"]
        assert body["checks"]["python"] is True

    def test_ready_status_field(self):
        """Ready endpoint should report 'ready' or 'degraded'."""
        handler = make_handler("/ready")
        handler.do_GET()
        body = json.loads(handler.wfile.getvalue())
        assert body["status"] in ("ready", "degraded")


class TestMetricsEndpoint:
    """Test the /metrics endpoint."""

    def test_metrics_returns_200(self):
        """Metrics endpoint should return 200."""
        handler = make_handler("/metrics")
        handler.do_GET()
        assert handler.response_code == 200

    def test_metrics_returns_system_info(self):
        """Metrics endpoint should include system info."""
        handler = make_handler("/metrics")
        handler.do_GET()
        body = json.loads(handler.wfile.getvalue())
        assert "uptime_seconds" in body
        assert "python_version" in body
        assert "platform" in body
        assert "pid" in body


class TestNotFound:
    """Test 404 handling."""

    def test_unknown_path_returns_404(self):
        """Unknown paths should return 404."""
        handler = make_handler("/unknown")
        handler.do_GET()
        assert handler.response_code == 404

    def test_404_includes_path(self):
        """404 response should include the requested path."""
        handler = make_handler("/bad-path")
        handler.do_GET()
        body = json.loads(handler.wfile.getvalue())
        assert body["path"] == "/bad-path"
