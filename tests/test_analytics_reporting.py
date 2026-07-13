import pytest
from unittest.mock import patch, MagicMock
import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analytics.reporter import AnalyticsReporter, ReportConfig
from src.api.main import app

client = TestClient(app)


class TestAnalyticsReporting:
    """Tests GA4/GSC analytics reporting, merging, anomaly detection, and endpoint."""

    def test_fetch_ga4_metrics(self):
        config = ReportConfig(property_id="987654")
        reporter = AnalyticsReporter(config)
        
        metrics = reporter.fetch_ga4_metrics("https://example.com/blog/seo")
        assert metrics["url"] == "https://example.com/blog/seo"
        assert "pageviews" in metrics
        assert "bounce_rate" in metrics
        assert "average_engagement_time_sec" in metrics

    def test_merge_ga4_and_gsc(self):
        config = ReportConfig(property_id="987654")
        reporter = AnalyticsReporter(config)
        
        ga4_data = {
            "url": "https://example.com/home",
            "pageviews": 1000,
            "bounce_rate": 0.35,
            "average_engagement_time_sec": 95.0
        }
        gsc_data = {
            "clicks": 50,
            "impressions": 1000,
            "ctr": 0.05,
            "position": 5.1
        }
        
        merged = reporter.merge_ga4_and_gsc(ga4_data, gsc_data)
        assert merged["url"] == "https://example.com/home"
        assert merged["clicks"] == 50
        assert merged["pageviews"] == 1000
        assert "merged_at" in merged

    def test_anomaly_detection_triggers(self):
        config = ReportConfig(property_id="987654")
        reporter = AnalyticsReporter(config)
        
        baseline = {
            "clicks": 100,
            "pageviews": 1000
        }
        
        # Scenario A: No significant drop
        current_ok = {
            "clicks": 90,     # 10% drop
            "pageviews": 950  # 5% drop
        }
        report_ok = reporter.detect_traffic_anomalies(current_ok, baseline)
        assert report_ok["anomaly_detected"] is False
        assert len(report_ok["reasons"]) == 0
        
        # Scenario B: Drop in clicks >= 20%
        current_drop_clicks = {
            "clicks": 75,     # 25% drop
            "pageviews": 950
        }
        report_drop = reporter.detect_traffic_anomalies(current_drop_clicks, baseline)
        assert report_drop["anomaly_detected"] is True
        assert any("click" in r for r in report_drop["reasons"])

        # Scenario C: Drop in pageviews >= 20%
        current_drop_pv = {
            "clicks": 95,
            "pageviews": 780  # 22% drop
        }
        report_drop_pv = reporter.detect_traffic_anomalies(current_drop_pv, baseline)
        assert report_drop_pv["anomaly_detected"] is True
        assert any("pageview" in r for r in report_drop_pv["reasons"])

    @patch("requests.post")
    def test_anomaly_alert_triggering(self, mock_post):
        # Setup mock post response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        config = ReportConfig(property_id="987654", webhook_url="https://hooks.slack.com/services/test")
        reporter = AnalyticsReporter(config)
        
        anomaly_report = {
            "anomaly_detected": True,
            "reasons": ["Significant drop in pageviews: 22% decrease."]
        }
        
        success = reporter.trigger_anomaly_alert(anomaly_report, "https://example.com/home")
        assert success is True
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_analytics_api_endpoint(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        response = client.get(
            "/api/v1/analytics",
            params={
                "url": "https://example.com/blog/container-alloydb",
                "property_id": "888123",
                "webhook_url": "https://hooks.slack.com/services/mockwebhook"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["url"] == "https://example.com/blog/container-alloydb"
        assert "metrics" in data
        assert "anomalies" in data
        assert data["alert_triggered"] is True
