"""Tests for Redirect Mapper."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import pytest
from redirect_mapper import RedirectMapper

class TestRedirectMapper:
    
    def test_add_get_redirect(self):
        mapper = RedirectMapper()
        mapper.add_redirect("/old", "/new", 301)
        
        target, status = mapper.get_redirect("/old")
        assert target == "/new"
        assert status == 301
        
    def test_invalid_status_code(self):
        mapper = RedirectMapper()
        with pytest.raises(ValueError):
            mapper.add_redirect("/old", "/new", 200)
            
    def test_preserve_query(self):
        mapper = RedirectMapper()
        mapper.add_redirect("/old", "/new")
        
        target, _ = mapper.get_redirect("/old?q=1")
        assert target == "/new?q=1"
        
    def test_no_preserve_query(self):
        mapper = RedirectMapper()
        mapper.add_redirect("/old", "/new", preserve_query=False)
        
        target, _ = mapper.get_redirect("/old?q=1")
        assert target == "/new"
        
    def test_detect_loops(self):
        mapper = RedirectMapper()
        mapper.add_redirect("/a", "/b")
        mapper.add_redirect("/b", "/c")
        mapper.add_redirect("/c", "/a")
        
        loops = mapper.detect_redirect_loops()
        assert len(loops) == 1
        # Loop should contain /a, /b, /c
        assert "/a" in loops[0]
        assert len(loops[0]) == 3
        
    def test_detect_chains(self):
        mapper = RedirectMapper()
        mapper.add_redirect("/a", "/b")
        mapper.add_redirect("/b", "/c")
        mapper.add_redirect("/c", "/d")
        
        # Max length 2 allows A->B->C (length 2 edges)
        chains = mapper.detect_redirect_chains(max_length=1)
        assert len(chains) == 1
        assert chains[0] == ["/a", "/b", "/c", "/d"]
        
    def test_generate_nginx_config(self):
        mapper = RedirectMapper()
        mapper.add_redirect("/old1", "/new1", 301)
        mapper.add_redirect("/old2", "/new2", 302)
        
        nginx = mapper.generate_nginx_config()
        assert "rewrite ^/old1$ /new1 permanent;" in nginx
        assert "rewrite ^/old2$ /new2 redirect;" in nginx
