"""Tests for RobotsTxtGenerator."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from robots_txt import RobotsTxtGenerator

class TestRobotsTxtGenerator:
    
    def test_generate_empty(self):
        gen = RobotsTxtGenerator()
        assert gen.generate() == ""
        
    def test_generate_with_rules(self):
        gen = RobotsTxtGenerator()
        gen.add_rule("*", "Disallow", "/admin/")
        gen.add_rule("*", "Allow", "/")
        gen.add_rule("Googlebot", "Disallow", "/private/")
        
        gen.add_sitemap("https://example.com/sitemap.xml")
        
        content = gen.generate()
        
        assert "User-agent: *" in content
        assert "Disallow: /admin/" in content
        assert "Allow: /" in content
        assert "User-agent: Googlebot" in content
        assert "Disallow: /private/" in content
        assert "Sitemap: https://example.com/sitemap.xml" in content
        
    def test_sorting_order(self):
        gen = RobotsTxtGenerator()
        gen.add_rule("Bingbot", "Disallow", "/b")
        gen.add_rule("*", "Disallow", "/a")
        
        content = gen.generate()
        
        # * should come first
        assert content.index("User-agent: *") < content.index("User-agent: Bingbot")
