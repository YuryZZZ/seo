import asyncio
import time
import logging
from typing import Any, Dict, Optional, Callable
import httpx

logger = logging.getLogger(__name__)

class CircuitBreakerOpenError(Exception):
    """Exception raised when the circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    A simple Circuit Breaker pattern implementation.
    
    States:
    - CLOSED: Normal operation. Requests go through.
    - OPEN: Too many failures. Requests fail immediately.
    - HALF_OPEN: Testing if the service is back after timeout.
    """
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = "CLOSED"
        self.failures = 0
        self.last_failure_time = 0.0
        self.half_open_calls = 0

    def record_success(self):
        """Record a successful request."""
        if self.state == "HALF_OPEN":
            logger.info("Circuit breaker closed: service recovered.")
            self.state = "CLOSED"
        self.failures = 0
        self.half_open_calls = 0

    def record_failure(self):
        """Record a failed request."""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.state == "CLOSED" and self.failures >= self.failure_threshold:
            logger.warning(f"Circuit breaker opened after {self.failures} failures.")
            self.state = "OPEN"
        elif self.state == "HALF_OPEN":
            logger.warning("Circuit breaker reopened: half-open test failed.")
            self.state = "OPEN"
            self.half_open_calls = 0

    def can_execute(self) -> bool:
        """Check if a request is allowed to execute."""
        if self.state == "CLOSED":
            return True
            
        if self.state == "OPEN":
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                logger.info("Circuit breaker half-open: testing service.")
                self.state = "HALF_OPEN"
                self.half_open_calls = 1
                return True
            return False
            
        if self.state == "HALF_OPEN":
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False
            
        return False


class ResilientHTTPClient:
    """
    HTTP client with connection pooling and circuit breaker built-in.
    """
    def __init__(
        self,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        timeout: float = 10.0,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0
    ):
        # Configure connection pooling limits
        limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections
        )
        
        self._client = httpx.AsyncClient(
            limits=limits,
            timeout=httpx.Timeout(timeout)
        )
        
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )

    async def close(self):
        """Close the underlying client."""
        await self._client.aclose()

    async def execute_request(
        self,
        method: str,
        url: str,
        **kwargs: Any
    ) -> httpx.Response:
        """
        Execute an HTTP request using the circuit breaker.
        """
        if not self.circuit_breaker.can_execute():
            raise CircuitBreakerOpenError(
                f"Circuit breaker is OPEN. Cannot execute {method} request to {url}."
            )

        try:
            response = await self._client.request(method, url, **kwargs)
            # 5xx errors are considered failures for the circuit breaker
            if response.status_code >= 500:
                self.circuit_breaker.record_failure()
                response.raise_for_status()
            
            # Record success for 2xx, 3xx, 4xx (4xx are client errors, not service outages)
            self.circuit_breaker.record_success()
            return response
            
        except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadError) as e:
            # Network-level errors trigger the circuit breaker
            self.circuit_breaker.record_failure()
            raise e

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.execute_request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.execute_request("POST", url, **kwargs)
        
    async def put(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.execute_request("PUT", url, **kwargs)
        
    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.execute_request("DELETE", url, **kwargs)
