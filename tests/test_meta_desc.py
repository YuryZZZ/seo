"""Tests for meta description generator."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import pytest
from content_utils import generate_meta_description

class TestGenerateMetaDescription:
    """Test auto-generating meta descriptions."""

    def test_extracts_from_first_p_tag(self):
        html = "<h1>Title</h1><p>This is the first paragraph. It has good content.</p><p>Second paragraph.</p>"
        desc = generate_meta_description(html)
        assert desc == "This is the first paragraph. It has good content."

    def test_skips_short_p_tags(self):
        html = "<p>Short.</p><p>This is the actual content paragraph that should be extracted as the meta description because it is long enough.</p>"
        desc = generate_meta_description(html)
        assert desc == "This is the actual content paragraph that should be extracted as the meta description because it is long enough."

    def test_truncates_long_content(self):
        html = "<p>" + "word " * 50 + "</p>"
        desc = generate_meta_description(html, max_length=100)
        assert len(desc) <= 100
        assert desc.endswith("...")

    def test_strips_html_tags(self):
        html = "<p>This is <strong>bold</strong> and <em>italic</em> text.</p>"
        desc = generate_meta_description(html)
        assert desc == "This is bold and italic text."

    def test_fallback_when_no_p_tags(self):
        html = "Just plain text without any paragraph tags but it is long enough to be a description."
        desc = generate_meta_description(html)
        assert desc == html

    def test_empty_content(self):
        assert generate_meta_description("") == ""
