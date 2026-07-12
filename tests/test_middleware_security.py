"""Tests for Security and Rate Limiting Middleware."""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from middleware_security import SecurityHeadersMiddleware, RateLimitingMiddleware

app = FastAPI()
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitingMiddleware, max_requests=3, window_seconds=2)

@app.get("/")
def read_root():
    return {"status": "ok"}

client = TestClient(app)

def test_security_headers():
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert response.headers["Content-Security-Policy"] == "default-src 'self'"

def test_rate_limiting():
    # Wait for window to expire from previous tests
    import time
    time.sleep(2.1)
    
    # First 3 requests should pass
    for _ in range(3):
        response = client.get("/")
        assert response.status_code == 200
        
    # 4th request should fail
    response = client.get("/")
    assert response.status_code == 429
    assert response.json()["detail"] == "Too Many Requests"
    
    # Wait for window to expire
    import time
    time.sleep(2.1)
    
    # Next request should pass again
    response = client.get("/")
    assert response.status_code == 200
