from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

try:
    from ...ab_testing import SEOTestCase, CloudflareWorkerGenerator, RollbackMechanism
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from ab_testing import SEOTestCase, CloudflareWorkerGenerator, RollbackMechanism

router = APIRouter(prefix="/api/v1/ab-test", tags=["ab-testing"])

# In-memory database of active A/B tests
_ab_tests_store: Dict[str, SEOTestCase] = {}


class CreateABTestSchema(BaseModel):
    test_id: str = Field(..., description="Unique test case identifier")
    url_pattern: str = Field(..., description="Regular expression pattern matching page paths")
    variant_a_title: str = Field(..., description="Title for Variant A (Control)")
    variant_b_title: str = Field(..., description="Title for Variant B (Challenger)")
    variant_a_meta: str = Field(..., description="Meta description for Variant A")
    variant_b_meta: str = Field(..., description="Meta description for Variant B")
    traffic_split: float = Field(0.5, description="Challenger traffic share (0.0 to 1.0)")


class UpdateMetricsSchema(BaseModel):
    impressions_a: int = Field(..., ge=0)
    clicks_a: int = Field(..., ge=0)
    impressions_b: int = Field(..., ge=0)
    clicks_b: int = Field(..., ge=0)


@router.post("", status_code=201)
async def create_ab_test(payload: CreateABTestSchema = Body(...)):
    """Creates a new edge-rewritten SEO A/B test and outputs a Cloudflare Worker script."""
    test_id = payload.test_id
    if test_id in _ab_tests_store:
        raise HTTPException(status_code=400, detail=f"A/B test with id {test_id} already exists")

    test_case = SEOTestCase(
        test_id=test_id,
        url_pattern=payload.url_pattern,
        variant_a_title=payload.variant_a_title,
        variant_b_title=payload.variant_b_title,
        variant_a_meta=payload.variant_a_meta,
        variant_b_meta=payload.variant_b_meta,
        traffic_split=payload.traffic_split
    )
    
    _ab_tests_store[test_id] = test_case
    
    worker_script = CloudflareWorkerGenerator.generate(
        test_id=test_id,
        url_pattern=payload.url_pattern,
        title_a=payload.variant_a_title,
        title_b=payload.variant_b_title,
        meta_a=payload.variant_a_meta,
        meta_b=payload.variant_b_meta,
        traffic_split=payload.traffic_split
    )

    return {
        "test": test_case.to_dict(),
        "cloudflare_worker_script": worker_script
    }


@router.get("/{test_id}")
async def get_ab_test(test_id: str):
    """Retrieves current state of an SEO A/B test."""
    if test_id not in _ab_tests_store:
        raise HTTPException(status_code=404, detail="A/B test not found")
    return _ab_tests_store[test_id].to_dict()


@router.post("/{test_id}/metrics")
async def update_ab_test_metrics(test_id: str, payload: UpdateMetricsSchema = Body(...)):
    """Pushes fresh behavioral metrics for the test case variants."""
    if test_id not in _ab_tests_store:
        raise HTTPException(status_code=404, detail="A/B test not found")

    test = _ab_tests_store[test_id]
    test.update_metrics(
        impressions_a=payload.impressions_a,
        clicks_a=payload.clicks_a,
        impressions_b=payload.impressions_b,
        clicks_b=payload.clicks_b
    )
    return {
        "status": "success",
        "test": test.to_dict()
    }


@router.post("/{test_id}/evaluate")
async def evaluate_ab_test(test_id: str, rollback_threshold: float = Query(-0.15, description="Relative CTR drop to trigger rollback")):
    """Performs statistical checks and initiates automated rollback if thresholds are violated."""
    if test_id not in _ab_tests_store:
        raise HTTPException(status_code=404, detail="A/B test not found")

    test = _ab_tests_store[test_id]
    mechanism = RollbackMechanism(rollback_threshold=rollback_threshold)
    result = mechanism.evaluate_test(test)
    return result


@router.get("", response_model=Dict[str, Any])
async def list_active_ab_tests():
    """Lists all configured SEO A/B test cases."""
    return {
        "total_tests": len(_ab_tests_store),
        "tests": [test.to_dict() for test in _ab_tests_store.values()]
    }
