import pytest
from fastapi.testclient import TestClient
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ab_testing import SEOTestCase, CloudflareWorkerGenerator, StatsCalculator, RollbackMechanism
from src.api.main import app

client = TestClient(app)


class TestABTesting:
    """Tests the edge A/B testing worker generation, Z-test calculations, and rollback logic."""

    def test_worker_generation(self):
        worker_js = CloudflareWorkerGenerator.generate(
            test_id="test_pricing_page",
            url_pattern="^/pricing$",
            title_a="Pricing Variant A",
            title_b="Pricing Variant B",
            meta_a="Meta desc A",
            meta_b="Meta desc B",
            traffic_split=0.4
        )
        
        assert "test_pricing_page" in worker_js
        assert "Pricing Variant A" in worker_js
        assert "Pricing Variant B" in worker_js
        assert "Meta desc A" in worker_js
        assert "Meta desc B" in worker_js
        assert "0.4" in worker_js

    def test_z_test_proportions(self):
        # Scenario 1: Same CTR
        res1 = StatsCalculator.z_test_proportions(1000, 50, 1000, 50)
        assert res1["ctr_a"] == 0.05
        assert res1["ctr_b"] == 0.05
        assert res1["p_value"] == 1.0
        assert res1["is_significant"] is False

        # Scenario 2: Variant B performs much better (significant improvement)
        res2 = StatsCalculator.z_test_proportions(10000, 100, 10000, 200)
        assert res2["ctr_a"] == 0.01
        assert res2["ctr_b"] == 0.02
        assert res2["is_significant"] is True
        assert res2["p_value"] < 0.05
        assert res2["relative_difference"] == 1.0  # +100%

        # Scenario 3: Zero case
        res3 = StatsCalculator.z_test_proportions(0, 0, 100, 5)
        assert res3["is_significant"] is False
        assert res3["p_value"] == 1.0

    def test_rollback_mechanism(self):
        test_case = SEOTestCase(
            test_id="test_rollback",
            url_pattern="^/product$",
            variant_a_title="A",
            variant_b_title="B",
            variant_a_meta="Meta A",
            variant_b_meta="Meta B",
            traffic_split=0.5
        )
        
        mechanism = RollbackMechanism(rollback_threshold=-0.15)
        
        # Metric state 1: B has minor fluctuations, no significance, no rollback
        test_case.update_metrics(10000, 200, 10000, 195)
        eval1 = mechanism.evaluate_test(test_case)
        assert eval1["rollback_triggered"] is False
        assert test_case.status == "active"
        
        # Metric state 2: B has statistically significant drop of 25% (200 vs 150)
        test_case.update_metrics(10000, 200, 10000, 150)
        eval2 = mechanism.evaluate_test(test_case)
        assert eval2["rollback_triggered"] is True
        assert test_case.status == "rolled_back"
        assert "ROLLBACK TRIGGERED" in eval2["message"]

    def test_ab_testing_endpoints(self):
        # 1. Create A/B test case
        payload = {
            "test_id": "test_endpoint_case",
            "url_pattern": "^/blog/post-1$",
            "variant_a_title": "Primary Title A",
            "variant_b_title": "Challenger Title B",
            "variant_a_meta": "Meta A",
            "variant_b_meta": "Meta B",
            "traffic_split": 0.5
        }
        
        response = client.post("/api/v1/ab-test", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "test" in data
        assert "cloudflare_worker_script" in data
        assert data["test"]["status"] == "active"
        
        # 2. Update metrics
        metrics_payload = {
            "impressions_a": 5000,
            "clicks_a": 250,
            "impressions_b": 5000,
            "clicks_b": 180  # 28% drop
        }
        response_metrics = client.post("/api/v1/ab-test/test_endpoint_case/metrics", json=metrics_payload)
        assert response_metrics.status_code == 200
        
        # 3. Evaluate and check auto-rollback
        response_eval = client.post("/api/v1/ab-test/test_endpoint_case/evaluate", params={"rollback_threshold": -0.15})
        assert response_eval.status_code == 200
        eval_data = response_eval.json()
        assert eval_data["rollback_triggered"] is True
        assert eval_data["status"] == "rolled_back"
        
        # 4. List tests
        response_list = client.get("/api/v1/ab-test")
        assert response_list.status_code == 200
        list_data = response_list.json()
        assert list_data["total_tests"] >= 1
