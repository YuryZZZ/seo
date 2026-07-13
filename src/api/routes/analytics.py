from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional

try:
    from ...analytics.reporter import AnalyticsReporter, ReportConfig
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from analytics.reporter import AnalyticsReporter, ReportConfig

router = APIRouter(prefix="/api/v1", tags=["analytics"])


@router.get("/analytics", response_model=Dict[str, Any])
async def get_combined_analytics(
    url: str = Query(..., description="The target URL to fetch analytics for"),
    property_id: str = Query("123456", description="The GA4 property ID"),
    webhook_url: Optional[str] = Query(None, description="Optional alert notification webhook URL")
) -> Dict[str, Any]:
    """
    Returns combined GA4 user behavioral metrics and GSC performance metrics.
    Automatically checks for traffic anomalies.
    """
    try:
        config = ReportConfig(property_id=property_id, webhook_url=webhook_url)
        reporter = AnalyticsReporter(config)
        
        # Simulating GSC data retrieval (or using query inputs in a real scenario)
        gsc_data = {
            "clicks": 120,
            "impressions": 2400,
            "ctr": 0.05,
            "position": 4.2
        }
        
        # Baseline data for anomaly check
        baseline_data = {
            "clicks": 200,
            "pageviews": 2000
        }
        
        ga4_metrics = reporter.fetch_ga4_metrics(url)
        merged = reporter.merge_ga4_and_gsc(ga4_metrics, gsc_data)
        anomalies = reporter.detect_traffic_anomalies(merged, baseline_data)
        
        # If webhook is active and anomaly exists, trigger alert
        alert_triggered = False
        if anomalies["anomaly_detected"] and webhook_url:
            alert_triggered = reporter.trigger_anomaly_alert(anomalies, url)
            
        return {
            "status": "success",
            "url": url,
            "metrics": merged,
            "anomalies": anomalies,
            "alert_triggered": alert_triggered
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analytics retrieval and analysis failed: {str(e)}"
        )
