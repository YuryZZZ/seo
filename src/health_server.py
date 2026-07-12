"""Lightweight HTTP health check server for Docker/K8s/Cloud Run probes.

Endpoints:
    /health  - Liveness probe (always 200 if server is running)
    /ready   - Readiness probe (checks config + dependencies)
    /metrics - Prometheus-style metrics (cache stats, uptime, memory)
"""

import json
import logging
import os
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

logger = logging.getLogger(__name__)

_start_time = time.time()


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Handles /health, /ready, and /metrics endpoints for container probes."""

    def do_GET(self):
        if self.path == "/health":
            self._respond(
                200,
                {
                    "status": "healthy",
                    "timestamp": time.time(),
                    "version": "2.1",
                    "service": "seo-geo-framework",
                    "uptime_seconds": round(time.time() - _start_time, 1),
                },
            )
        elif self.path == "/ready":
            checks = {"python": True, "config": False, "cache": False, "validation": False}
            try:
                from src.config import get_config
                config = get_config()
                issues = config.validate()
                checks["config"] = len(issues) == 0
            except Exception:
                pass

            try:
                from src.cache import cache
                checks["cache"] = cache is not None
            except Exception:
                pass

            try:
                from src.validation import ValidationGates
                checks["validation"] = True
            except ImportError:
                pass

            all_ready = all(checks.values())
            self._respond(
                200 if all_ready else 503,
                {
                    "status": "ready" if all_ready else "degraded",
                    "checks": checks,
                },
            )
        elif self.path == "/metrics":
            self._respond(200, self._collect_metrics())
        else:
            self._respond(404, {"error": "Not found", "path": self.path})

    def _collect_metrics(self) -> dict:
        """Collect framework metrics for monitoring."""
        import platform

        metrics = {
            "uptime_seconds": round(time.time() - _start_time, 1),
            "python_version": platform.python_version(),
            "platform": platform.system(),
            "pid": os.getpid(),
        }

        # Memory usage
        try:
            import psutil
            proc = psutil.Process(os.getpid())
            mem = proc.memory_info()
            metrics["memory_rss_mb"] = round(mem.rss / 1024 / 1024, 1)
            metrics["memory_vms_mb"] = round(mem.vms / 1024 / 1024, 1)
        except ImportError:
            pass

        # Cache stats
        try:
            from src.cache import cache
            if cache and hasattr(cache, 'stats'):
                metrics["cache"] = cache.stats()
            elif cache and hasattr(cache, '_cache'):
                metrics["cache"] = {
                    "entries": len(cache._cache) if hasattr(cache._cache, '__len__') else 0,
                }
        except Exception:
            metrics["cache"] = {"available": False}

        return metrics

    def _respond(self, code: int, body: dict):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-cache, no-store")
        self.end_headers()
        self.wfile.write(json.dumps(body, default=str).encode())

    def log_message(self, format, *args):
        # Suppress health check noise in logs
        if "/health" not in (args[0] if args else ""):
            logger.info(f"Health check: {format % args}")


def start_health_server(port: int = 8080, daemon: bool = True) -> HTTPServer:
    """Start health check server in background thread."""
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=daemon)
    thread.start()
    logger.info(f"Health server started on port {port}")
    return server


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = start_health_server(8080, daemon=False)
    print("Health server running on http://0.0.0.0:8080")
    print("  /health  - Liveness probe")
    print("  /ready   - Readiness probe")
    print("  /metrics - Monitoring metrics")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.shutdown()

