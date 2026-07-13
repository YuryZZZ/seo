from fastapi import FastAPI
from .health import router as health_router
from .jobs import router as jobs_router
from .agents import router as agents_router
from .framework import router as framework_router
from .pseo import router as pseo_router
from .analytics import router as analytics_router
from .ab_testing import router as ab_testing_router
from .decay import router as decay_router

__all__ = ["health_router", "jobs_router", "agents_router", "framework_router", "pseo_router", "analytics_router", "ab_testing_router", "decay_router", "include_routers"]


def include_routers(app: FastAPI):
    """Include all API routers in the FastAPI application."""
    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(agents_router)
    app.include_router(framework_router)
    app.include_router(pseo_router)
    app.include_router(analytics_router)
    app.include_router(ab_testing_router)
    app.include_router(decay_router)
