"""Technical SEO Auditing module."""

import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Set
from urllib.parse import urljoin, urlparse

class SEOAuditor:
    """Performs technical SEO audits on a website."""
    
    def __init__(self, base_url: str, max_pages: int = 100):
        self.base_url = base_url
        self.max_pages = max_pages
        self.visited_urls: Set[str] = set()
        self.broken_links: List[Dict[str, Any]] = []
        self.pages_audited: List[Dict[str, Any]] = []
        
    def _is_internal(self, url: str) -> bool:
        """Check if URL belongs to the base domain."""
        base_netloc = urlparse(self.base_url).netloc
        target_netloc = urlparse(url).netloc
        return base_netloc == target_netloc or not target_netloc

    def crawl_and_audit(self, start_url: str = None) -> Dict[str, Any]:
        """Crawl the website and perform SEO audits.
        
        Returns:
            Dictionary containing audit report.
        """
        queue = [start_url or self.base_url]
        
        # We will use a synchronous client for simplicity in this minimal crawler
        with httpx.Client(follow_redirects=True, timeout=10.0) as client:
            while queue and len(self.visited_urls) < self.max_pages:
                url = queue.pop(0)
                
                if url in self.visited_urls:
                    continue
                    
                self.visited_urls.add(url)
                
                try:
                    response = client.get(url)
                    
                    if response.status_code >= 400:
                        self.broken_links.append({
                            "url": url,
                            "status": response.status_code
                        })
                        continue
                        
                    # Only parse HTML
                    content_type = response.headers.get("content-type", "")
                    if "text/html" not in content_type:
                        continue
                        
                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    # Audit current page
                    audit_result = self._audit_page(url, soup)
                    self.pages_audited.append(audit_result)
                    
                    # Discover links
                    for link in soup.find_all("a", href=True):
                        href = link["href"]
                        full_url = urljoin(url, href)
                        
                        # Remove fragment
                        full_url = full_url.split("#")[0]
                        
                        if self._is_internal(full_url) and full_url not in self.visited_urls and full_url not in queue:
                            queue.append(full_url)
                            
                except httpx.RequestError as e:
                    self.broken_links.append({
                        "url": url,
                        "error": str(e)
                    })
                    
        return self.generate_report()
        
    def _audit_page(self, url: str, soup: BeautifulSoup) -> Dict[str, Any]:
        """Audit a single page's HTML."""
        result = {
            "url": url,
            "issues": []
        }
        
        # 1. Title length
        title_tag = soup.find("title")
        if not title_tag:
            result["issues"].append("Missing <title> tag")
        else:
            title_len = len(title_tag.text.strip())
            if title_len < 10:
                result["issues"].append(f"Title too short ({title_len} chars)")
            elif title_len > 60:
                result["issues"].append(f"Title too long ({title_len} chars)")
                
        # 2. Meta description length
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if not meta_desc or not meta_desc.get("content"):
            result["issues"].append("Missing meta description")
        else:
            desc_len = len(meta_desc["content"].strip())
            if desc_len < 50:
                result["issues"].append(f"Meta description too short ({desc_len} chars)")
            elif desc_len > 160:
                result["issues"].append(f"Meta description too long ({desc_len} chars)")
                
        # 3. Missing alt tags
        images = soup.find_all("img")
        images_missing_alt = [img for img in images if not img.get("alt")]
        if images_missing_alt:
            result["issues"].append(f"{len(images_missing_alt)} images missing 'alt' attribute")
            
        # 4. H1 tag checks
        h1_tags = soup.find_all("h1")
        if len(h1_tags) == 0:
            result["issues"].append("Missing H1 tag")
        elif len(h1_tags) > 1:
            result["issues"].append(f"Multiple H1 tags found ({len(h1_tags)})")
            
        return result
        
    def generate_report(self) -> Dict[str, Any]:
        """Generate final audit report."""
        total_pages = len(self.pages_audited)
        pages_with_issues = len([p for p in self.pages_audited if p["issues"]])
        
        return {
            "base_url": self.base_url,
            "pages_crawled": len(self.visited_urls),
            "broken_links": self.broken_links,
            "pages_audited": total_pages,
            "pages_with_issues": pages_with_issues,
            "audit_details": self.pages_audited
        }
