from fastapi import APIRouter, HTTPException
from typing import Dict, Any

try:
    from ...pseo_engine import PSEOEngine
    from ..schemas import PSEOBulkGenerateRequest, PSEOBulkGenerateResponse
except ImportError:
    # Handle import fallbacks for direct script run or integration scenarios
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from pseo_engine import PSEOEngine
    from api.schemas import PSEOBulkGenerateRequest, PSEOBulkGenerateResponse

router = APIRouter(prefix="/api/v1", tags=["pseo"])


@router.post("/pseo/bulk", response_model=PSEOBulkGenerateResponse)
async def bulk_generate_pseo_pages(request: PSEOBulkGenerateRequest) -> PSEOBulkGenerateResponse:
    """
    Bulk generates programmatic SEO pages from a template configuration and a dataset.
    """
    try:
        engine = PSEOEngine(
            title_template=request.templates.title_template,
            meta_desc_template=request.templates.meta_description_template,
            h1_template=request.templates.h1_template,
            body_template=request.templates.body_template,
        )

        results = engine.bulk_render(
            dataset=request.dataset,
            spin=request.spin,
            seed_key=request.seed_key,
        )

        # Normalize results to match the Pydantic schema
        pages = []
        for r in results:
            pages.append({
                "row_index": r["row_index"],
                "data": r["data"],
                "rendered": {
                    "title": r["rendered"]["title"],
                    "meta_description": r["rendered"]["meta_description"],
                    "h1": r["rendered"]["h1"],
                    "body": r["rendered"]["body"],
                }
            })

        return PSEOBulkGenerateResponse(
            status="success",
            pages=pages
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Programmatic SEO bulk generation failed: {str(e)}"
        )
