"""Tests for SEO Meta Tags Generator."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from seo_tags import SEOTagGenerator

class TestSEOTagGenerator:
    
    def test_generate_canonical_tag(self):
        tag = SEOTagGenerator.generate_canonical_tag("https://example.com/page")
        assert tag == '<link rel="canonical" href="https://example.com/page" />'
        
    def test_generate_canonical_tag_empty(self):
        assert SEOTagGenerator.generate_canonical_tag("") == ""
        
    def test_generate_open_graph_tags(self):
        tags = SEOTagGenerator.generate_open_graph_tags(
            title="My Page",
            url="https://example.com",
            image="https://example.com/img.jpg",
            description='This is "great"'
        )
        assert 'property="og:title" content="My Page"' in tags
        assert 'property="og:url" content="https://example.com"' in tags
        assert 'property="og:image" content="https://example.com/img.jpg"' in tags
        assert 'property="og:description" content="This is &quot;great&quot;"' in tags
        
    def test_generate_twitter_card_tags(self):
        tags = SEOTagGenerator.generate_twitter_card_tags(
            title="Twitter Title",
            site="@mysite"
        )
        assert 'name="twitter:card" content="summary_large_image"' in tags
        assert 'name="twitter:title" content="Twitter Title"' in tags
        assert 'name="twitter:site" content="@mysite"' in tags
