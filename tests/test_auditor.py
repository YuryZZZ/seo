"""Tests for SEOAuditor."""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from auditor import SEOAuditor
from bs4 import BeautifulSoup

class TestSEOAuditor:
    
    def test_is_internal(self):
        auditor = SEOAuditor("https://example.com")
        
        assert auditor._is_internal("https://example.com/about") is True
        assert auditor._is_internal("/contact") is True
        assert auditor._is_internal("https://google.com") is False
        
    def test_audit_page(self):
        auditor = SEOAuditor("https://example.com")
        
        html = """
        <html>
            <head>
                <title>Short</title>
                <meta name="description" content="Too short desc">
            </head>
            <body>
                <img src="no-alt.jpg">
                <img src="good.jpg" alt="Valid alt text">
                <!-- Missing H1 -->
            </body>
        </html>
        """
        
        soup = BeautifulSoup(html, "html.parser")
        result = auditor._audit_page("https://example.com", soup)
        
        issues = result["issues"]
        assert "Title too short (5 chars)" in issues
        assert "Meta description too short (14 chars)" in issues
        assert "1 images missing 'alt' attribute" in issues
        assert "Missing H1 tag" in issues
        
    @patch('auditor.httpx.Client')
    def test_crawl_and_audit(self, mock_client_class):
        # Setup mock client and responses
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Good page response
        good_response = MagicMock()
        good_response.status_code = 200
        good_response.headers = {"content-type": "text/html"}
        good_response.text = '<html><head><title>A completely valid and properly long title for testing</title><meta name="description" content="This is a properly long description that definitely exceeds fifty characters so it does not trigger any warnings during our SEO audit testing suite."></head><body><h1>Main Title</h1><a href="/about">About</a><a href="/404-page">Broken</a><a href="https://external.com">Ext</a></body></html>'
        
        # Another good page response
        about_response = MagicMock()
        about_response.status_code = 200
        about_response.headers = {"content-type": "text/html"}
        about_response.text = "<html><head><title>About</title></head><body><h1>About</h1></body></html>"
        
        # 404 response
        broken_response = MagicMock()
        broken_response.status_code = 404
        
        def side_effect(url):
            if url == "https://example.com":
                return good_response
            elif url == "https://example.com/about":
                return about_response
            elif url == "https://example.com/404-page":
                return broken_response
            raise Exception("Unexpected URL")
            
        mock_client.get.side_effect = side_effect
        
        auditor = SEOAuditor("https://example.com", max_pages=5)
        report = auditor.crawl_and_audit()
        
        assert report["pages_crawled"] == 3
        assert report["pages_audited"] == 2
        
        assert len(report["broken_links"]) == 1
        assert report["broken_links"][0]["url"] == "https://example.com/404-page"
        assert report["broken_links"][0]["status"] == 404
        
        assert report["pages_with_issues"] == 1 # the about page has short title/missing meta description
