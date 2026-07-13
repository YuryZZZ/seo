"""
Main application entry point for SEO/GEO Framework
FastAPI server with all agent endpoints
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from src.api.routes import include_routers
from src.middleware_security import SecurityHeadersMiddleware, RateLimitingMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SEO_GEO_Framework")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    logger.info("🚀 Starting SEO/GEO Framework API...")
    
    # Initialize database pool (if configured)
    try:
        from src.database import init_db_pool
        await init_db_pool()
        logger.info("✅ Database pool initialized")
    except Exception as e:
        logger.warning(f"Database pool not initialized: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down SEO/GEO Framework API...")
    
    # Close database pool
    try:
        from src.database import close_db_pool
        await close_db_pool()
        logger.info("✅ Database pool closed")
    except Exception as e:
        logger.warning(f"Error closing database pool: {e}")


app = FastAPI(
    title="SEO/GEO Framework API",
    description="""
    Comprehensive SEO and GEO optimization framework with 10 specialized agents:
    
    ## Agents
    - **ORCHESTRATOR**: Coordinates all workflow phases (0-9)
    - **POLICY_RESEARCHER**: Google guidelines, helpful content policies
    - **GEO_RESEARCHER**: SERP snapshots, PAA extraction, entity mapping
    - **IA_ARCHITECT**: H2 questions (>50%), citable blocks
    - **MASTER_COPYWRITER**: BLUF paragraphs, snippet bait, AI tell removal
    - **MEDIA_STUDIO**: Image prompts, alt text, SEO filenames
    - **SCHEMA_ENGINEER**: JSON-LD generation, DOM validation
    - **QA_GATEKEEPER**: 12 validation gates
    - **SYNDICATION_BROADCASTER**: Pinterest, YouTube payloads
    - **ANALYTICS_ITERATION**: GSC/GA4 tracking, iteration cycles
    
    ## Endpoints
    - `/api/v1/orchestrate` - Run full workflow
    - `/api/v1/research/geo` - GEO research
    - `/api/v1/research/policy` - Policy research
    - `/api/v1/copywrite` - Content generation
    - `/api/v1/schema` - JSON-LD generation
    - `/api/v1/validate` - Validation gates
    - `/api/v1/syndicate` - Content syndication
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security and Rate Limiting
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitingMiddleware, max_requests=100, window_seconds=60)


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for consistent error responses."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": str(request.state.get("request_time", ""))
        }
    )


# Include API routes
include_routers(app)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "SEO/GEO Framework API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "agents": 10,
        "validation_gates": 12,
        "core_columns": 80,
        "extended_columns": 80
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {
        "status": "healthy",
        "service": "seo-geo-framework"
    }


@app.get("/api/v1/profile")
async def profile_endpoint():
    """Performance profiling endpoint."""
    import psutil
    process = psutil.Process()
    memory_info = process.memory_info()
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_rss_mb": memory_info.rss / (1024 * 1024),
        "memory_vms_mb": memory_info.vms / (1024 * 1024),
        "threads": process.num_threads()
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    # Check database connectivity
    db_ready = True
    try:
        from src.database import check_db_connection
        db_ready = await check_db_connection()
    except Exception:
        db_ready = False
    
    return {
        "ready": db_ready,
        "checks": {
            "database": "ok" if db_ready else "error"
        }
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
