import pytest
import os
import sys
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.decay import ContentDecayAnalyzer, ContentRefreshStrategy, DiffComparisonTool
from src.api.main import app


class TestDecayAutoRefresh:
    """
    Test suite for the Content Decay & Auto-Refresh logic and endpoints.
    """

    def test_calculate_time_decay(self):
        analyzer = ContentDecayAnalyzer(time_decay_half_life_days=100.0)
        
        # Test case: 0 days elapsed -> 0 decay score
        now_iso = datetime.utcnow().isoformat()
        assert analyzer.calculate_time_decay(now_iso) == 0.0
        
        # Test case: 100 days elapsed (one half life) -> decay score should be around 0.5 (1.0 - exp(-ln(2)*1))
        half_life_ago = (datetime.utcnow() - timedelta(days=100)).isoformat()
        assert 0.49 <= analyzer.calculate_time_decay(half_life_ago) <= 0.51

    def test_calculate_traffic_drop(self):
        analyzer = ContentDecayAnalyzer()
        
        # Baseline 90-day clicks = 900 -> 30-day equivalent is 300 clicks.
        # Current 30-day clicks = 150. Traffic drop = (300 - 150) / 300 = 50% (0.50).
        assert analyzer.calculate_traffic_drop(current_30_clicks=150, baseline_90_clicks=900) == 0.50
        
        # Baseline 90-day clicks = 900 -> 30-day equivalent is 300 clicks.
        # Current 30-day clicks = 350. Traffic drop = 0.0 (no drop).
        assert analyzer.calculate_traffic_drop(current_30_clicks=350, baseline_90_clicks=900) == 0.0

    def test_calculate_decay_score(self):
        analyzer = ContentDecayAnalyzer(time_decay_half_life_days=100.0)
        
        # 100 days ago (time decay = 0.5)
        last_modified = (datetime.utcnow() - timedelta(days=100)).isoformat()
        # Current 150 clicks vs 900 baseline clicks (traffic drop = 0.5)
        # Score = 0.5 * 0.7 + 0.5 * 0.3 = 0.5
        score = analyzer.calculate_decay_score(
            last_modified_iso=last_modified,
            current_30_clicks=150,
            baseline_90_clicks=900,
            weight_traffic=0.7,
            weight_time=0.3
        )
        assert 0.49 <= score <= 0.51

    def test_refresh_strategy_prompt_and_fallback(self):
        strategy = ContentRefreshStrategy()
        content = "This is some old content about SEO in 2024."
        
        prompt = strategy.generate_refresh_prompt(
            current_content=content,
            focus_keyword="seo trends",
            missing_lsi=["SGE", "EEAT"],
            target_year=2026
        )
        
        assert "2026" in prompt
        assert "SGE, EEAT" in prompt
        assert "seo trends" in prompt
        
        # Test offline fallback (without LLM config)
        refreshed = strategy.refresh_page_content(
            current_content=content,
            focus_keyword="seo trends",
            missing_lsi=["SGE", "EEAT"],
            target_year=2026
        )
        assert "2026" in refreshed
        assert "SGE, EEAT" in refreshed

    def test_diff_comparison_tool(self):
        old_text = "Deploying containers is fast.\nWe love Docker."
        new_text = "Deploying containers is fast.\nWe love Kubernetes."
        
        html_diff = DiffComparisonTool.generate_html_diff(old_text, new_text)
        assert "Deploying" in html_diff
        assert "Docker" in html_diff
        assert "Kubernetes" in html_diff

    def test_api_decay_endpoints(self):
        client = TestClient(app)
        
        # 1. Test queue retrieval
        response = client.get("/api/v1/decay/queue")
        assert response.status_code == 200
        data = response.json()
        
        # Should return at least 1 decaying page (like example.com/blog/seo-trends-2024 which has high traffic drop and age)
        assert len(data) >= 1
        assert "seo-trends-2024" in data[0]["url"]
        assert data[0]["decay_score"] > 0.5
        
        # 2. Test refresh endpoint
        target_url = "https://example.com/blog/seo-trends-2024"
        refresh_payload = {
            "url": target_url,
            "missing_lsi": ["SGE", "Search Generative Experience"],
            "target_year": 2026
        }
        
        refresh_response = client.post("/api/v1/decay/refresh", json=refresh_payload)
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        
        assert refresh_data["url"] == target_url
        assert "2026" in refresh_data["refreshed_content"]
        assert "SGE" in refresh_data["refreshed_content"]
        assert "html_diff" in refresh_data
