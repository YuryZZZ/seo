import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api.main import app

client = TestClient(app)


class TestPSEOAPI:
    """Tests the programmatic SEO bulk generation API endpoints."""

    def test_bulk_generate_pseo_pages(self):
        payload = {
            "templates": {
                "title_template": "Best {{ service }} in {{ location }}",
                "meta_description_template": "Looking for {{ service }} in {{ location }}? Try our {premium|top-rated} package.",
                "h1_template": "Hire the best {{ service }}",
                "body_template": "We provide {world-class|exceptional} {{ service }} starting from {{ price }}."
            },
            "dataset": [
                {"service": "Plumbing", "location": "Bristol", "price": "£150", "slug": "plumbing-bristol"},
                {"service": "Electrician", "location": "Bath", "price": "£200", "slug": "electrician-bath"}
            ],
            "spin": True,
            "seed_key": "slug"
        }

        response = client.post("/api/v1/pseo/bulk", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["pages"]) == 2

        # Check structure of rendered row
        page_1 = data["pages"][0]
        assert page_1["row_index"] == 0
        assert page_1["data"]["location"] == "Bristol"
        assert page_1["rendered"]["title"] == "Best Plumbing in Bristol"
        assert any(opt in page_1["rendered"]["meta_description"] for opt in ["premium", "top-rated"])

        page_2 = data["pages"][1]
        assert page_2["row_index"] == 1
        assert page_2["data"]["location"] == "Bath"
        assert page_2["rendered"]["title"] == "Best Electrician in Bath"

    def test_bulk_generate_without_spinning(self):
        payload = {
            "templates": {
                "title_template": "{{ service }} - {{ location }}",
                "meta_description_template": "Best {{ service }}",
                "h1_template": "{{ service }} Specialist",
                "body_template": "Price: {{ price }}"
            },
            "dataset": [
                {"service": "SEO", "location": "London", "price": "£1000"}
            ],
            "spin": False
        }

        response = client.post("/api/v1/pseo/bulk", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["pages"]) == 1
        assert data["pages"][0]["rendered"]["title"] == "SEO - London"

    def test_bulk_generate_rejects_missing_templates(self):
        payload = {
            "dataset": [
                {"service": "SEO", "location": "London"}
            ]
        }
        response = client.post("/api/v1/pseo/bulk", json=payload)
        assert response.status_code == 422
