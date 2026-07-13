import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from starlette.types import ASGIApp
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.middleware_security import RateLimitingMiddleware
from src.celery_app import celery_app, run_seo_orchestrator_job_task
from src.main import app as legacy_app
from src.api.main import app as main_app


class TestEnterpriseFeatures:
    """Test suite for Celery tasks, Redis rate limiter, and K8s configuration existence."""

    def test_celery_task_registry(self):
        """Verify Celery task registry contains the run_seo_orchestrator_job task."""
        assert "run_seo_orchestrator_job" in celery_app.tasks
        task = celery_app.tasks["run_seo_orchestrator_job"]
        assert task is not None

    @pytest.mark.asyncio
    async def test_redis_rate_limiter_increment(self):
        """Verify distributed rate limiter makes correct calls to Redis client."""
        mock_app = MagicMock(spec=ASGIApp)
        middleware = RateLimitingMiddleware(app=mock_app, max_requests=2, window_seconds=60)
        
        # Mock Redis client pipelines
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe
        
        # First request: count = 1, ttl = -1 (means expire should be set)
        mock_pipe.execute.return_value = (1, -1)
        middleware.redis_client = mock_redis
        
        # Test mock request dispatch
        mock_request = MagicMock()
        mock_request.client.host = "1.2.3.4"
        
        async def mock_call_next(req):
            return "success"
            
        res = await middleware.dispatch(mock_request, mock_call_next)
        assert res == "success"
        mock_redis.expire.assert_called_with("ratelimit:1.2.3.4", 60)

    @pytest.mark.asyncio
    async def test_redis_rate_limiter_exceeded(self):
        """Verify distributed rate limiter returns 429 when max requests exceeded."""
        mock_app = MagicMock(spec=ASGIApp)
        middleware = RateLimitingMiddleware(app=mock_app, max_requests=2, window_seconds=60)
        
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe
        
        # Simulate request count = 3 (greater than max_requests = 2)
        mock_pipe.execute.return_value = (3, 10)
        middleware.redis_client = mock_redis
        
        mock_request = MagicMock()
        mock_request.client.host = "1.2.3.4"
        
        async def mock_call_next(req):
            return "success"
            
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_redis_rate_limiter_fallback(self):
        """Verify distributed rate limiter falls back to memory limit when Redis throws."""
        mock_app = MagicMock(spec=ASGIApp)
        middleware = RateLimitingMiddleware(app=mock_app, max_requests=1, window_seconds=60)
        
        # Simulating broken Redis connection
        mock_redis = MagicMock()
        mock_redis.pipeline.side_effect = Exception("Connection lost")
        middleware.redis_client = mock_redis
        
        mock_request = MagicMock()
        mock_request.client.host = "5.6.7.8"
        
        async def mock_call_next(req):
            return MagicMock()
            
        # First request passes
        res1 = await middleware.dispatch(mock_request, mock_call_next)
        assert res1 != "Too Many Requests"
        
        # Second request blocked by memory fallback (max_requests = 1)
        res2 = await middleware.dispatch(mock_request, mock_call_next)
        assert res2.status_code == 429

    def test_kubernetes_manifests_exist(self):
        """Ensure K8s deployment manifests are correctly created in the workspace."""
        assert os.path.exists("k8s/deployment.yaml")
        assert os.path.exists("k8s/service.yaml")
