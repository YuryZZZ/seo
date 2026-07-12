"""Security and Rate Limiting Middleware."""

import time
from typing import Dict, Tuple
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
    """Simple in-memory rate limiting middleware."""
    
    def __init__(self, app: ASGIApp, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # dict mapping IP to (request_count, window_start_time)
        self.clients: Dict[str, Tuple[int, float]] = {}
        
    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        
        if client_ip in self.clients:
            count, start_time = self.clients[client_ip]
            if now - start_time > self.window_seconds:
                # Reset window
                self.clients[client_ip] = (1, now)
            else:
                if count >= self.max_requests:
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Too Many Requests"}
                    )
                self.clients[client_ip] = (count + 1, start_time)
        else:
            self.clients[client_ip] = (1, now)
            
        return await call_next(request)
