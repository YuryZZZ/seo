from fastapi import APIRouter, Query
from datetime import datetime
from typing import List, Optional
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.api.schemas import HealthResponse

router = APIRouter(prefix="/api/v1", tags=["health"])

@router.get("/health", response_model=HealthResponse, status_code=200)
async def health_check():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow()
    )

@router.get("/ready", status_code=200)
async def readiness_probe():
    return {"status": "ready"}

@router.get("/metrics", status_code=200)
async def metrics(
    target: Optional[str] = Query(None, description="Target text to analyze"),
    reference: Optional[List[str]] = Query(None, description="Reference texts/competitor snippets to compare against")
):
    base_metrics = {
        "jobs_total": 0,
        "jobs_completed": 0,
        "jobs_failed": 0,
        "agents_available": 6
    }
    
    if target and reference:
        try:
            try:
                from ...ml.vector_search import VectorSearchEngine
            except ImportError:
                from ml.vector_search import VectorSearchEngine
                
            engine = VectorSearchEngine()
            gap_analysis = engine.analyze_semantic_gaps(reference, [target])
            base_metrics["semantic_similarity"] = gap_analysis
        except Exception as e:
            base_metrics["semantic_similarity_error"] = str(e)
            
    return base_metrics
