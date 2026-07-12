"""Basic Memory Leakage Tests."""

import sys
import os
import psutil
import gc
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from auditor import SEOAuditor
from bs4 import BeautifulSoup

def test_auditor_memory_leak():
    """Ensure that the auditor doesn't excessively leak memory after clearing references."""
    process = psutil.Process()
    
    # Force garbage collection and get baseline memory
    gc.collect()
    baseline_memory = process.memory_info().rss
    
    auditor = SEOAuditor("https://example.com", max_pages=100)
    
    # Simulate adding large amounts of data
    for i in range(1000):
        soup = BeautifulSoup(f"<html><head><title>Page {i}</title></head><body><h1>H1</h1></body></html>", "html.parser")
        auditor._audit_page(f"https://example.com/page{i}", soup)
        auditor.pages_audited.append({"url": f"https://example.com/page{i}", "issues": []})
        
    # Delete auditor and collect garbage
    del auditor
    gc.collect()
    
    final_memory = process.memory_info().rss
    memory_diff_mb = (final_memory - baseline_memory) / (1024 * 1024)
    
    # Assert memory difference is less than 5MB
    # Note: memory profiling in Python can be flaky due to OS-level allocators.
    assert memory_diff_mb < 5.0, f"Memory leaked: {memory_diff_mb} MB"
