from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

try:
    from ...decay import ContentDecayAnalyzer, ContentRefreshStrategy, DiffComparisonTool
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from decay import ContentDecayAnalyzer, ContentRefreshStrategy, DiffComparisonTool

router = APIRouter(prefix="/api/v1/decay", tags=["decay"])

# Mock decaying pages repository
_decay_store: Dict[str, Dict[str, Any]] = {
    "https://example.com/blog/seo-trends-2024": {
        "url": "https://example.com/blog/seo-trends-2024",
        "title": "Top SEO Trends for 2024",
        "content": "In 2024, SEO is changing fast. Businesses must look at AI Search and SGE strategies.",
        "focus_keyword": "seo trends",
        "last_modified": "2024-01-15T12:00:00",
        "current_30_clicks": 150,
        "baseline_90_clicks": 1800,  # Adjusted 30-day baseline is 600, so a 75% drop
    },
    "https://example.com/blog/alloydb-containers-2025": {
        "url": "https://example.com/blog/alloydb-containers-2025",
        "title": "AlloyDB Omni Containers in 2025",
        "content": "Deploying AlloyDB Omni containers is the best way to run local databases in 2025.",
        "focus_keyword": "alloydb containers",
        "last_modified": "2025-01-01T08:00:00",
        "current_30_clicks": 400,
        "baseline_90_clicks": 1500,  # Adjusted 30-day baseline is 500, so a 20% drop
    }
}


class RefreshPayload(BaseModel):
    url: str = Field(..., description="Target page URL")
    missing_lsi: List[str] = Field(default_factory=list, description="Missing LSI entities/keywords to inject")
    target_year: int = Field(2026, description="Target year to update")


@router.get("/queue", status_code=200)
async def get_decay_queue():
    """
    Returns list of decaying pages that need a content refresh.
    Excludes pages with low decay score (<= 0.5).
    """
    analyzer = ContentDecayAnalyzer()
    queue = []
    
    for url, info in _decay_store.items():
        score = analyzer.calculate_decay_score(
            last_modified_iso=info["last_modified"],
            current_30_clicks=info["current_30_clicks"],
            baseline_90_clicks=info["baseline_90_clicks"]
        )
        
        # Only queue if decay score is greater than 0.5
        if score > 0.5:
            queue.append({
                "url": url,
                "title": info["title"],
                "decay_score": score,
                "last_modified": info["last_modified"],
                "days_since_modification": (datetime.utcnow() - datetime.fromisoformat(info["last_modified"])).days
            })
            
    # Sort queue by decay score descending
    queue.sort(key=lambda x: x["decay_score"], reverse=True)
    return queue


@router.post("/refresh", status_code=200)
async def refresh_content(payload: RefreshPayload = Body(...)):
    """
    Triggers refresh of old/decayed page, generating updated content and a side-by-side diff.
    """
    url = payload.url
    if url not in _decay_store:
        raise HTTPException(status_code=404, detail=f"Page with URL '{url}' not found in decay store.")
        
    info = _decay_store[url]
    refresher = ContentRefreshStrategy()
    
    old_content = info["content"]
    refreshed_content = refresher.refresh_page_content(
        current_content=old_content,
        focus_keyword=info["focus_keyword"],
        missing_lsi=payload.missing_lsi,
        target_year=payload.target_year
    )
    
    # Generate HTML diff
    html_diff = DiffComparisonTool.generate_html_diff(old_content, refreshed_content)
    
    # Update in-memory DB
    info["content"] = refreshed_content
    info["last_modified"] = datetime.utcnow().isoformat()
    info["current_30_clicks"] = info["baseline_90_clicks"] // 3 # reset clicks to match baseline (simulated)
    
    return {
        "url": url,
        "old_content": old_content,
        "refreshed_content": refreshed_content,
        "html_diff": html_diff,
        "last_modified": info["last_modified"]
    }
