"""Tests for Local SEO and Internationalization."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from local_intl import LocalSEOManager, InternationalizationManager

class TestLocalSEOManager:
    
    def test_multi_location_schema(self):
        base_org = {
            "name": "Acme Corp",
            "url": "https://acme.com"
        }
        
        locations = [
            {"name": "Acme London", "address": "123 London St", "telephone": "123-456-7890"},
            {"address": "456 Paris Ave", "url": "https://acme.com/paris"}
        ]
        
        schema = LocalSEOManager.generate_multi_location_schema(base_org, locations)
        
        assert schema["@type"] == "Organization"
        assert schema["name"] == "Acme Corp"
        assert len(schema["department"]) == 2
        
        dept1 = schema["department"][0]
        assert dept1["@type"] == "LocalBusiness"
        assert dept1["name"] == "Acme London"
        assert dept1["telephone"] == "123-456-7890"
        
        dept2 = schema["department"][1]
        assert dept2["name"] == "Acme Corp" # Falls back to base_org name
        assert dept2["address"] == "456 Paris Ave"
        assert dept2["url"] == "https://acme.com/paris"
        
    def test_geo_keyword_variations(self):
        keywords = LocalSEOManager.generate_geo_keyword_variations("plumber", ["London", "Paris"])
        
        assert len(keywords) == 6
        assert "plumber in London" in keywords
        assert "Paris plumber" in keywords
        assert "best plumber London" in keywords

class TestInternationalizationManager:
    
    def test_hreflang_tags(self):
        alternates = {
            "en": "https://example.com/en",
            "fr": "https://example.com/fr",
            "x-default": "https://example.com/en"
        }
        
        tags = InternationalizationManager.generate_hreflang_tags("https://example.com/en", alternates)
        
        assert 'hreflang="en"' in tags
        assert 'hreflang="fr"' in tags
        assert 'hreflang="x-default"' in tags
        assert 'href="https://example.com/fr"' in tags
        
    def test_multilingual_sitemap(self):
        urls = [
            {
                "loc": "https://example.com/en/page",
                "alternates": {"fr": "https://example.com/fr/page", "de": "https://example.com/de/page"}
            },
            {
                "loc": "https://example.com/en/about"
            }
        ]
        
        sitemap = InternationalizationManager.add_multilingual_sitemap_entries(urls)
        
        assert "<loc>https://example.com/en/page</loc>" in sitemap
        assert '<xhtml:link rel="alternate" hreflang="fr" href="https://example.com/fr/page"/>' in sitemap
        assert '<xhtml:link rel="alternate" hreflang="de" href="https://example.com/de/page"/>' in sitemap
        
        # Second URL should not have alternate links
        about_section = sitemap.split("<loc>https://example.com/en/about</loc>")[1]
        assert "<xhtml:link" not in about_section
        
    def test_seo_translation(self):
        result = InternationalizationManager.translate_with_seo_context("Hello world", "es", "hola")
        assert "[Translated to es focusing on 'hola']:" in result
        assert "Hello world" in result
