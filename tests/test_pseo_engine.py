import os
import tempfile
import json
import pytest
from pseo_engine import PSEODataParser, SpinTextGenerator, PSEOEngine


class TestPSEODataParser:
    """Tests CSV and JSON data source parsing."""

    def test_parse_csv(self):
        csv_content = "location,price,service\nLondon,£500,Web Design\nManchester,£400,SEO Optimization\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
            tmp.write(csv_content)
            tmp_path = tmp.name

        try:
            data = PSEODataParser.parse_csv(tmp_path)
            assert len(data) == 2
            assert data[0]["location"] == "London"
            assert data[0]["price"] == "£500"
            assert data[1]["service"] == "SEO Optimization"
        finally:
            os.remove(tmp_path)

    def test_parse_json(self):
        json_data = [
            {"location": "London", "price": "£500", "service": "Web Design"},
            {"location": "Manchester", "price": "£400", "service": "SEO"},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(json_data, tmp)
            tmp_path = tmp.name

        try:
            data = PSEODataParser.parse_json(tmp_path)
            assert len(data) == 2
            assert data[0]["location"] == "London"
            assert data[1]["service"] == "SEO"
        finally:
            os.remove(tmp_path)

    def test_parse_json_single_object(self):
        json_data = {"location": "London", "price": "£500", "service": "Web Design"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(json_data, tmp)
            tmp_path = tmp.name

        try:
            data = PSEODataParser.parse_json(tmp_path)
            assert len(data) == 1
            assert data[0]["location"] == "London"
        finally:
            os.remove(tmp_path)


class TestSpinTextGenerator:
    """Tests spin-text processing, determinism, and uniqueness."""

    def test_basic_spinning(self):
        text = "Get {affordable|cheap|low-cost} SEO."
        spun = SpinTextGenerator.spin(text)
        assert spun in [
            "Get affordable SEO.",
            "Get cheap SEO.",
            "Get low-cost SEO.",
        ]

    def test_nested_spinning(self):
        text = "This is {simple {and fast|and quick}|easy}."
        # Possible results:
        # - "This is simple and fast."
        # - "This is simple and quick."
        # - "This is easy."
        spun = SpinTextGenerator.spin(text)
        assert spun in [
            "This is simple and fast.",
            "This is simple and quick.",
            "This is easy.",
        ]

    def test_seed_determinism(self):
        text = "This is {highly|extremely|very} unique {content|material}."
        # Without seed, it can vary. With seed, it must be stable across multiple calls
        spun_1 = SpinTextGenerator.spin(text, seed="seed-a")
        spun_2 = SpinTextGenerator.spin(text, seed="seed-a")
        spun_3 = SpinTextGenerator.spin(text, seed="seed-b")

        assert spun_1 == spun_2

        # Verify other seeds can generate different options
        # (Though technically they *could* collision, md5 hash makes it statistically distinct for long lists)
        different_spun_found = False
        for i in range(100):
            other = SpinTextGenerator.spin(text, seed=f"seed-{i}")
            if other != spun_1:
                different_spun_found = True
                break
        assert different_spun_found


class TestPSEOEngine:
    """Tests Jinja2 rendering + spin integration."""

    def test_engine_render_page(self):
        engine = PSEOEngine(
            title_template="Best {{ service }} in {{ location }}",
            meta_desc_template="Looking for {{ service }} in {{ location }}? Try our {premium|top-rated} package.",
            h1_template="Hire the best {{ service }}",
            body_template="We provide {world-class|exceptional} {{ service }} starting from {{ price }}.",
        )

        row = {
            "service": "Plumbing",
            "location": "Bristol",
            "price": "£150",
            "slug": "plumbing-bristol",
        }

        # Render without spin
        res_no_spin = engine.render_page(row, spin=False)
        assert res_no_spin["title"] == "Best Plumbing in Bristol"
        assert "{premium|top-rated}" in res_no_spin["meta_description"]
        assert "Hire the best Plumbing" in res_no_spin["h1"]

        # Render with spin
        res_spin = engine.render_page(row, spin=True, seed_key="slug")
        assert res_spin["title"] == "Best Plumbing in Bristol"
        assert any(opt in res_spin["meta_description"] for opt in ["premium", "top-rated"])
        assert any(opt in res_spin["body"] for opt in ["world-class", "exceptional"])

    def test_bulk_render(self):
        engine = PSEOEngine(
            title_template="{{ service }} - {{ location }}",
            meta_desc_template="Best {{ service }}",
            h1_template="{{ service }} Specialist",
            body_template="Price: {{ price }}",
        )

        dataset = [
            {"service": "SEO", "location": "London", "price": "£1000"},
            {"service": "PPC", "location": "Leeds", "price": "£800"},
        ]

        results = engine.bulk_render(dataset, spin=False)
        assert len(results) == 2
        assert results[0]["row_index"] == 0
        assert results[0]["data"]["location"] == "London"
        assert results[0]["rendered"]["title"] == "SEO - London"
        assert results[1]["rendered"]["title"] == "PPC - Leeds"
