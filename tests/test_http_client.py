"""Tests for ResilientHTTPClient and CircuitBreaker."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import pytest
import time
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from http_client import CircuitBreaker, CircuitBreakerOpenError, ResilientHTTPClient


class TestCircuitBreaker:
    """Test CircuitBreaker state machine."""

    def test_initial_state(self):
        cb = CircuitBreaker()
        assert cb.state == "CLOSED"
        assert cb.can_execute() is True

    def test_transitions_to_open_on_failures(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "CLOSED"
        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.can_execute() is False

    @patch("http_client.time.time")
    def test_transitions_to_half_open_after_timeout(self, mock_time):
        mock_time.return_value = 100.0
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0)
        cb.record_failure()
        assert cb.state == "OPEN"
        
        # Less than timeout
        mock_time.return_value = 105.0
        assert cb.can_execute() is False
        assert cb.state == "OPEN"
        
        # After timeout
        mock_time.return_value = 115.0
        assert cb.can_execute() is True
        assert cb.state == "HALF_OPEN"

    def test_reopens_on_failure_in_half_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.0)
        cb.record_failure()
        assert cb.can_execute() is True  # Transitions to HALF_OPEN
        assert cb.state == "HALF_OPEN"
        
        cb.record_failure()
        assert cb.state == "OPEN"

    def test_closes_on_success_in_half_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.0)
        cb.record_failure()
        assert cb.can_execute() is True  # Transitions to HALF_OPEN
        
        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.failures == 0

    @patch("http_client.time.time")
    def test_half_open_max_calls(self, mock_time):
        mock_time.return_value = 100.0
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0, half_open_max_calls=2)
        cb.record_failure()
        
        mock_time.return_value = 115.0 # After timeout
        
        assert cb.can_execute() is True  # Call 1
        assert cb.can_execute() is True  # Call 2
        assert cb.can_execute() is False # Reached max calls for testing


@pytest.mark.asyncio
class TestResilientHTTPClient:
    """Test ResilientHTTPClient operations."""

    async def test_successful_request_records_success(self):
        client = ResilientHTTPClient()
        
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        
        client._client.request = AsyncMock(return_value=mock_response)
        
        # Mock circuit breaker to verify record_success is called
        client.circuit_breaker = MagicMock(spec=CircuitBreaker)
        client.circuit_breaker.can_execute.return_value = True
        
        response = await client.get("https://example.com")
        
        assert response.status_code == 200
        client.circuit_breaker.record_success.assert_called_once()
        await client.close()

    async def test_server_error_records_failure(self):
        client = ResilientHTTPClient()
        
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("500", request=MagicMock(), response=mock_response)
        
        client._client.request = AsyncMock(return_value=mock_response)
        
        client.circuit_breaker = MagicMock(spec=CircuitBreaker)
        client.circuit_breaker.can_execute.return_value = True
        
        with pytest.raises(httpx.HTTPStatusError):
            await client.get("https://example.com")
            
        client.circuit_breaker.record_failure.assert_called_once()
        await client.close()

    async def test_network_error_records_failure(self):
        client = ResilientHTTPClient()
        
        client._client.request = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
        
        client.circuit_breaker = MagicMock(spec=CircuitBreaker)
        client.circuit_breaker.can_execute.return_value = True
        
        with pytest.raises(httpx.ConnectError):
            await client.get("https://example.com")
            
        client.circuit_breaker.record_failure.assert_called_once()
        await client.close()

    async def test_circuit_breaker_open_blocks_request(self):
        client = ResilientHTTPClient()
        
        client.circuit_breaker = MagicMock(spec=CircuitBreaker)
        client.circuit_breaker.can_execute.return_value = False
        
        with pytest.raises(CircuitBreakerOpenError):
            await client.get("https://example.com")
            
        await client.close()

    async def test_methods_delegation(self):
        client = ResilientHTTPClient()
        client.execute_request = AsyncMock()
        
        await client.get("url")
        client.execute_request.assert_called_with("GET", "url")
        
        await client.post("url", json={"a": 1})
        client.execute_request.assert_called_with("POST", "url", json={"a": 1})
        
        await client.put("url")
        client.execute_request.assert_called_with("PUT", "url")
        
        await client.delete("url")
        client.execute_request.assert_called_with("DELETE", "url")
        
        await client.close()
