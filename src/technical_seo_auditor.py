import logging
import re
import json
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

@dataclass
class AuditResult:
    url: str
    status_code: int
    title: Optional[str] = None
    meta_description: Optional[str] = None
    h1_tags: List[str] = field(default_factory=list)
    schema_markup: List[Dict] = field(default_factory=list)
    internal_links: List[str] = field(default_factory=list)
    external_links: List[str] = field(default_factory=list)
    images_without_alt: List[str] = field(default_factory=list)
    canonical_url: Optional[str] = None
    load_time_ms: Optional[float] = None
    errors: List[str] = field(default_factory=list)

@dataclass
class BrokenLink:
    source_url: str
    target_url: str
    status_code: int
    link_text: str = ""
    suggested_redirect: Optional[str] = None
    severity: str = "high"

@dataclass
class PageSpeedMetrics:
    url: str
    performance_score: Optional[float] = None
    lcp: Optional[float] = None
    fcp: Optional[float] = None
    cls: Optional[float] = None
    errors: List[str] = field(default_factory=list)

class TechnicalSEOAuditor:
    def __init__(self, site_url: str, api_keys: Optional[Dict[str, str]] = None):
        self.site_url = site_url.rstrip('/')
        self.api_keys = api_keys or {}
        self.crawled_pages: Dict[str, AuditResult] = {}
        self.broken_links: List[BrokenLink] = []
        self.pagespeed_metrics: Dict[str, PageSpeedMetrics] = {}
        self.visited_urls: Set[str] = set()
        self.session_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'}
        self.crawl_budget_report: Optional[Dict[str, Any]] = None
    
    def _normalize_url(self, url: str) -> str:
        url = url.split('#')[0].split('?')[0]
        if not url.startswith(('http://', 'https://')):
            url = urljoin(self.site_url, url)
        return url.rstrip('/')
    
    def _is_internal_url(self, url: str) -> bool:
        parsed = urlparse(url)
        site_parsed = urlparse(self.site_url)
        return parsed.netloc == site_parsed.netloc
    
    def _fetch_page(self, url: str) -> tuple:
        try:
            import requests
            resp = requests.get(url, headers=self.session_headers, timeout=15)
            return resp.status_code, resp.text, None
        except Exception as e:
            return 0, '', str(e)
    
    def _parse_html(self, html: str, url: str) -> AuditResult:
        result = AuditResult(url=url, status_code=200)
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            title_tag = soup.find('title')
            result.title = title_tag.get_text() if title_tag else None
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            result.meta_description = meta_desc.get('content') if meta_desc else None
            result.h1_tags = [h.get_text().strip() for h in soup.find_all('h1')]
            canonical = soup.find('link', rel='canonical')
            result.canonical_url = canonical.get('href') if canonical else None
            for link in soup.find_all('a', href=True):
                href = self._normalize_url(link['href'])
                if self._is_internal_url(href):
                    result.internal_links.append(href)
                else:
                    result.external_links.append(href)
            for img in soup.find_all('img'):
                if not img.get('alt'):
                    result.images_without_alt.append(img.get('src', 'unknown'))
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    schema = json.loads(script.string)
                    result.schema_markup.append(schema)
                except:
                    pass
        except ImportError:
            result.errors.append('beautifulsoup4 not installed')
        except Exception as e:
            result.errors.append(str(e))
        return result
    
    def crawl_site(self, max_pages: int = 100) -> List[AuditResult]:
        to_visit = [self.site_url]
        results = []
        while to_visit and len(self.visited_urls) < max_pages:
            url = to_visit.pop(0)
            url = self._normalize_url(url)
            if url in self.visited_urls or not self._is_internal_url(url):
                continue
            if any(ext in url.lower() for ext in ['.jpg', '.png', '.gif', '.pdf', '.zip']):
                continue
            self.visited_urls.add(url)
            status, html, error = self._fetch_page(url)
            if error:
                result = AuditResult(url=url, status_code=0, errors=[error])
            else:
                result = self._parse_html(html, url)
                result.status_code = status
                for link in result.internal_links:
                    if link not in self.visited_urls:
                        to_visit.append(link)
            self.crawled_pages[url] = result
            results.append(result)
        return results
    
    def check_broken_links(self, pages: List[AuditResult] = None) -> List[BrokenLink]:
        pages_to_check = pages or list(self.crawled_pages.values())
        broken = []
        for page in pages_to_check:
            all_links = list(set(page.internal_links + page.external_links))
            for link in all_links[:20]:
                if link in self.visited_urls:
                    continue
                try:
                    import requests
                    resp = requests.head(link, headers=self.session_headers, timeout=10, allow_redirects=True)
                    if resp.status_code >= 400:
                        broken.append(BrokenLink(source_url=page.url, target_url=link, status_code=resp.status_code, severity="critical" if resp.status_code == 404 else "high"))
                except Exception as e:
                    broken.append(BrokenLink(source_url=page.url, target_url=link, status_code=0, severity="medium"))
                self.visited_urls.add(link)
        self.broken_links = broken
        return broken
    
    def check_meta_tags(self, url: str) -> Dict[str, Any]:
        if url not in self.crawled_pages:
            return {"error": "Page not crawled"}
        page = self.crawled_pages[url]
        issues = []
        if not page.title:
            issues.append({"type": "missing_title", "severity": "critical"})
        elif len(page.title) > 60:
            issues.append({"type": "title_too_long", "severity": "warning", "length": len(page.title)})
        if not page.meta_description:
            issues.append({"type": "missing_meta_description", "severity": "critical"})
        elif len(page.meta_description) > 160:
            issues.append({"type": "meta_too_long", "severity": "warning", "length": len(page.meta_description)})
        if len(page.h1_tags) == 0:
            issues.append({"type": "missing_h1", "severity": "critical"})
        elif len(page.h1_tags) > 1:
            issues.append({"type": "multiple_h1", "severity": "warning", "count": len(page.h1_tags)})
        return {"url": url, "title": page.title, "meta_description": page.meta_description, "h1_count": len(page.h1_tags), "issues": issues}
    
    def audit_crawl_budget(self, log_content: str) -> Dict[str, Any]:
        """
        Runs crawl budget analysis using LogAnalyzer.
        """
        try:
            from .log_analyzer import LogAnalyzer
        except ImportError:
            from log_analyzer import LogAnalyzer
            
        analyzer = LogAnalyzer()
        summary = analyzer.parse_log_file(log_content)
        frequencies = analyzer.calculate_crawl_frequency()
        traps = analyzer.detect_crawl_traps()
        recommendations = analyzer.generate_recommendations()
        
        self.crawl_budget_report = {
            "summary": summary,
            "crawl_frequencies": frequencies,
            "crawl_traps": traps,
            "recommendations": recommendations
        }
        return self.crawl_budget_report

    def generate_audit_report(self) -> Dict[str, Any]:
        total_pages = len(self.crawled_pages)
        if total_pages == 0 and not self.crawl_budget_report:
            return {"error": "No pages crawled and no log analysis done"}
        pages_missing_titles = len([p for p in self.crawled_pages.values() if not p.title])
        pages_missing_descriptions = len([p for p in self.crawled_pages.values() if not p.meta_description])
        
        report = {
            "site_url": self.site_url,
            "audit_timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_pages_crawled": total_pages,
                "broken_links_found": len(self.broken_links),
                "pages_missing_titles": pages_missing_titles,
                "pages_missing_descriptions": pages_missing_descriptions
            },
            "broken_links": [{"source": bl.source_url, "target": bl.target_url, "status": bl.status_code} for bl in self.broken_links[:50]],
            "pages": {url: {"title": r.title, "h1_count": len(r.h1_tags)} for url, r in list(self.crawled_pages.items())[:20]}
        }
        
        if self.crawl_budget_report:
            report["crawl_budget"] = self.crawl_budget_report
            
        return report
    
    def auto_fix_404(self, broken_links: List[BrokenLink] = None) -> List[Dict[str, Any]]:
        links = broken_links or self.broken_links
        fixes = []
        for link in links:
            if link.status_code == 404:
                suggested = self._find_similar_page(link.target_url)
                fixes.append({"broken_url": link.target_url, "source_page": link.source_url, "suggested_redirect": suggested, "redirect_type": "301"})
        return fixes
    
    def _find_similar_page(self, broken_url: str) -> str:
        path = urlparse(broken_url).path
        segments = [s for s in path.split('/') if s]
        if segments:
            for url, page in self.crawled_pages.items():
                if segments[-1] in url.lower():
                    return url
        return self.site_url
    
    def prioritize_fixes(self, issues: List[Dict] = None) -> List[Dict[str, Any]]:
        all_issues = issues or []
        for bl in self.broken_links:
            all_issues.append({"type": "broken_link", "url": bl.target_url, "severity": bl.severity, "impact_score": 100 if bl.status_code == 404 else 80})
        for url, page in self.crawled_pages.items():
            if not page.title:
                all_issues.append({"type": "missing_title", "url": url, "severity": "critical", "impact_score": 90})
            if not page.meta_description:
                all_issues.append({"type": "missing_meta", "url": url, "severity": "critical", "impact_score": 85})
        all_issues.sort(key=lambda x: x.get('impact_score', 0), reverse=True)
        return all_issues[:50]
