"""Tests for XML Sitemap Generator."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from sitemap_generator import SitemapGenerator

class TestSitemapGenerator:
    
    def test_generate_empty(self):
        xml = SitemapGenerator.generate([])
        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
        assert '<urlset' in xml
        assert 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"' in xml
        
    def test_generate_with_urls(self):
        urls = [
            {"loc": "https://example.com/", "lastmod": "2026-07-12", "changefreq": "daily", "priority": "1.0"},
            {"loc": "https://example.com/about"}
        ]
        
        xml = SitemapGenerator.generate(urls)
        
        assert '<loc>https://example.com/</loc>' in xml
        assert '<lastmod>2026-07-12</lastmod>' in xml
        assert '<changefreq>daily</changefreq>' in xml
        assert '<priority>1.0</priority>' in xml
        
        assert '<loc>https://example.com/about</loc>' in xml
        # Second URL shouldn't have priority if not specified
        assert xml.count('<priority>') == 1
