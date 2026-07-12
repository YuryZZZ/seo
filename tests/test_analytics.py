"""Tests for analytics module."""

import sys
import os
import tempfile
import csv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from seo_analytics import GoogleSearchConsoleAPI, SEOAnalyticsDashboard, KeywordTracker, AnomalyDetector, ReportExporter

class TestAnalytics:
    
    def test_gsc_api_placeholder(self):
        client = GoogleSearchConsoleAPI()
        
        data = client.get_search_analytics("https://example.com", "2023-01-01", "2023-01-31")
        assert len(data) == 2
        assert data[0]["clicks"] == 150
        
    def test_seo_dashboard(self):
        client = GoogleSearchConsoleAPI()
        dashboard = SEOAnalyticsDashboard(client)
        
        metrics = dashboard.generate_metrics_summary("https://example.com", "2023-01-01", "2023-01-31")
        
        assert metrics["site_url"] == "https://example.com"
        assert metrics["total_clicks"] == 230
        assert metrics["total_impressions"] == 7000
        
        # 150*12.5 + 80*8.2 = 1875 + 656 = 2531 / 7000 = 0.3615
        assert round(metrics["average_position"], 2) == 11.27
        assert round(metrics["average_ctr"], 4) == 0.0329
        assert "seo tools" in metrics["top_queries"]
        
    def test_keyword_tracker(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "history.json")
            tracker = KeywordTracker(storage_path=file_path)
            
            tracker.record_ranking("seo tools", "https://example.com/tools", 10.5, "2023-01-01")
            tracker.record_ranking("seo tools", "https://example.com/tools", 8.2, "2023-01-02")
            
            history = tracker.get_history("seo tools")
            assert len(history) == 2
            assert history[0]["position"] == 10.5
            assert history[1]["position"] == 8.2
            
            # Test reload from file
            tracker2 = KeywordTracker(storage_path=file_path)
            assert len(tracker2.get_history("seo tools")) == 2
            
    def test_anomaly_detector(self):
        # 100 to 70 is a 30% drop (threshold is 20) -> True
        assert AnomalyDetector.detect_traffic_drop(70, 100) is True
        
        # 100 to 90 is a 10% drop -> False
        assert AnomalyDetector.detect_traffic_drop(90, 100) is False
        
        # 100 to 110 is a spike (negative drop) -> False
        assert AnomalyDetector.detect_traffic_drop(110, 100) is False
        
        # 0 previous clicks
        assert AnomalyDetector.detect_traffic_drop(10, 0) is False
        
    def test_report_exporter(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "report.csv")
            
            metrics = [
                {"keyword": "test", "clicks": 10, "position": 5},
                {"keyword": "demo", "clicks": 20, "position": 2}
            ]
            
            ReportExporter.export_to_csv(metrics, file_path)
            
            assert os.path.exists(file_path)
            
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                assert len(rows) == 2
                assert rows[0]["keyword"] == "test"
                assert rows[0]["clicks"] == "10"
                assert rows[1]["position"] == "2"
