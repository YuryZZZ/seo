"""Security and Rate Limiting Middleware."""

import time
from typing import Dict, Tuple, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to responses."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Distributed Redis-backed rate limiting middleware with in-memory fallback."""
    
    def __init__(self, app: ASGIApp, max_requests: int = 100, window_seconds: int = 60, redis_url: Optional[str] = None):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        
        # Redis configuration
        self.redis_client = None
        import os
        url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            import redis
            self.redis_client = redis.Redis.from_url(url, socket_timeout=2.0)
            self.redis_client.ping()
        except Exception:
            self.redis_client = None
            
        # dict mapping IP to (request_count, window_start_time)
        self.clients: Dict[str, Tuple[int, float]] = {}
        
    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        
        if self.redis_client:
            try:
                key = f"ratelimit:{client_ip}"
                pipe = self.redis_client.pipeline()
                pipe.incr(key)
                pipe.ttl(key)
                count, ttl = pipe.execute()
                
                if ttl == -1:
                    self.redis_client.expire(key, self.window_seconds)
                    
                if count > self.max_requests:
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Too Many Requests"}
                    )
            except Exception:
                # Redis failure fallback to memory limit
                if not await self._check_memory_rate_limit(client_ip, now):
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Too Many Requests"}
                    )
        else:
            if not await self._check_memory_rate_limit(client_ip, now):
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too Many Requests"}
                )
                
        return await call_next(request)
        
    async def _check_memory_rate_limit(self, client_ip: str, now: float) -> bool:
        if client_ip in self.clients:
            count, start_time = self.clients[client_ip]
            if now - start_time > self.window_seconds:
                self.clients[client_ip] = (1, now)
                return True
            else:
                if count >= self.max_requests:
                    return False
                self.clients[client_ip] = (count + 1, start_time)
                return True
        else:
            self.clients[client_ip] = (1, now)
            return True
