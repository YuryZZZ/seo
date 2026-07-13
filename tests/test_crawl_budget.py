import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.log_analyzer import LogAnalyzer
from src.technical_seo_auditor import TechnicalSEOAuditor


class TestCrawlBudget:
    """Tests log parsing, crawl frequency, crawl traps detection, and technical SEO integration."""

    @pytest.fixture
    def sample_log_content(self):
        return (
            '127.0.0.1 - - [10/Oct/2026:13:55:36 +0000] "GET /index.html HTTP/1.1" 200 2326 "referrer" "Mozilla/5.0 Googlebot"\n'
            '127.0.0.1 - - [10/Oct/2026:13:56:01 +0000] "GET /deep/path/to/folder/nest/file.html HTTP/1.1" 200 5000 "referrer" "Mozilla/5.0 Bingbot"\n'
            '127.0.0.1 - - [10/Oct/2026:13:57:12 +0000] "GET /index.html HTTP/1.1" 200 2326 "referrer" "Mozilla/5.0 Googlebot"\n'
            '127.0.0.1 - - [10/Oct/2026:13:58:15 +0000] "GET /products?id=123&sort=desc&color=blue&size=m HTTP/1.1" 200 8000 "referrer" "Mozilla/5.0 Googlebot"\n'
            '127.0.0.1 - - [10/Oct/2026:13:59:30 +0000] "GET /redirect-loop HTTP/1.1" 301 150 "referrer" "Mozilla/5.0 Bingbot"\n'
            '127.0.0.1 - - [10/Oct/2026:13:59:31 +0000] "GET /redirect-loop HTTP/1.1" 301 150 "referrer" "Mozilla/5.0 Bingbot"\n'
            '127.0.0.1 - - [10/Oct/2026:13:59:32 +0000] "GET /redirect-loop HTTP/1.1" 301 150 "referrer" "Mozilla/5.0 Bingbot"\n'
            '127.0.0.1 - - [10/Oct/2026:13:59:33 +0000] "GET /redirect-loop HTTP/1.1" 301 150 "referrer" "Mozilla/5.0 Bingbot"\n'
            '127.0.0.1 - - [10/Oct/2026:13:59:34 +0000] "GET /redirect-loop HTTP/1.1" 301 150 "referrer" "Mozilla/5.0 Bingbot"\n'
            '127.0.0.1 - - [10/Oct/2026:13:59:35 +0000] "GET /redirect-loop HTTP/1.1" 301 150 "referrer" "Mozilla/5.0 Bingbot"\n'
            '127.0.0.1 - - [10/Oct/2026:13:59:36 +0000] "GET /redirect-loop HTTP/1.1" 301 150 "referrer" "Mozilla/5.0 Bingbot"\n'
            '127.0.0.1 - - [10/Oct/2026:13:59:37 +0000] "GET /redirect-loop HTTP/1.1" 301 150 "referrer" "Mozilla/5.0 Bingbot"\n'
            '127.0.0.1 - - [10/Oct/2026:13:59:38 +0000] "GET /redirect-loop HTTP/1.1" 301 150 "referrer" "Mozilla/5.0 Bingbot"\n'
            '127.0.0.1 - - [10/Oct/2026:13:59:39 +0000] "GET /redirect-loop HTTP/1.1" 301 150 "referrer" "Mozilla/5.0 Bingbot"\n'
            '127.0.0.1 - - [10/Oct/2026:13:59:40 +0000] "GET /redirect-loop HTTP/1.1" 301 150 "referrer" "Mozilla/5.0 Bingbot"\n'
        )

    def test_log_parsing(self, sample_log_content):
        analyzer = LogAnalyzer()
        summary = analyzer.parse_log_file(sample_log_content)
        
        assert summary["googlebot_hits_count"] == 3
        assert summary["bingbot_hits_count"] == 12
        assert summary["total_lines_parsed"] == 15

    def test_crawl_frequency(self, sample_log_content):
        analyzer = LogAnalyzer()
        analyzer.parse_log_file(sample_log_content)
        frequencies = analyzer.calculate_crawl_frequency()
        
        assert "/index.html" in frequencies
        assert frequencies["/index.html"]["googlebot"] == 2
        assert frequencies["/index.html"]["total"] == 2

    def test_crawl_traps_detection(self, sample_log_content):
        analyzer = LogAnalyzer()
        analyzer.parse_log_file(sample_log_content)
        traps = analyzer.detect_crawl_traps()
        
        # Check excessive query params trap
        assert len(traps["excessive_params"]) == 1
        assert "products?id=123&sort=desc&color=blue&size=m" in traps["excessive_params"][0]
        
        # Check deep directory structure trap
        assert len(traps["deep_paths"]) == 1
        assert "deep/path/to/folder/nest/file.html" in traps["deep_paths"][0]
        
        # Check redirect loop trap (triggered > 10 hits)
        assert len(traps["potential_loops"]) == 1
        assert "redirect-loop" in traps["potential_loops"][0]

    def test_generate_recommendations(self, sample_log_content):
        analyzer = LogAnalyzer()
        analyzer.parse_log_file(sample_log_content)
        recommendations = analyzer.generate_recommendations()
        
        assert any("robots.txt" in r for r in recommendations)
        assert any("canonical" in r for r in recommendations)
        assert any("redirect" in r for r in recommendations)

    def test_technical_auditor_integration(self, sample_log_content):
        auditor = TechnicalSEOAuditor("https://example.com")
        report = auditor.audit_crawl_budget(sample_log_content)
        
        assert "summary" in report
        assert "crawl_frequencies" in report
        assert "crawl_traps" in report
        assert "recommendations" in report
        
        full_report = auditor.generate_audit_report()
        assert "crawl_budget" in full_report
        assert full_report["crawl_budget"]["summary"]["googlebot_hits_count"] == 3
