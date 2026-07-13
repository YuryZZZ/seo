import re
import logging
from typing import Dict, List, Any, Tuple, Set, Optional
from collections import defaultdict
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class LogAnalyzer:
    """
    Parses web server log files (Nginx, Apache) to analyze crawl budget,
    filter search engine bots (Googlebot, Bingbot), and detect crawl traps.
    """
    
    # Combined/Common Log Format regex
    LOG_PATTERN = re.compile(
        r'(?P<ip>\S+)\s+\S+\s+(?P<user>\S+)\s+\[(?P<timestamp>[^\]]+)\]\s+'
        r'"(?P<method>\S+)\s+(?P<url>\S+)\s+HTTP/[0-9.]+"\s+'
        r'(?P<status>\d+)\s+(?P<bytes>\S+)(?:\s+"(?P<referrer>[^"]*)"\s+"(?P<user_agent>[^"]*)")?'
    )

    def __init__(self):
        self.googlebot_hits = []
        self.bingbot_hits = []
        self.other_hits = []
        
    def parse_log_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parses a single Common/Combined log line."""
        match = self.LOG_PATTERN.match(line)
        if not match:
            return None
        return match.groupdict()

    def parse_log_file(self, log_content: str) -> Dict[str, Any]:
        """
        Parses full log contents and separates Googlebot and Bingbot hits.
        """
        self.googlebot_hits = []
        self.bingbot_hits = []
        self.other_hits = []
        
        lines = log_content.splitlines()
        for line in lines:
            parsed = self.parse_log_line(line)
            if not parsed:
                continue
            
            ua = parsed.get("user_agent", "") or ""
            ua_lower = ua.lower()
            
            if "googlebot" in ua_lower:
                self.googlebot_hits.append(parsed)
            elif "bingbot" in ua_lower:
                self.bingbot_hits.append(parsed)
            else:
                self.other_hits.append(parsed)
                
        return {
            "total_lines_parsed": len(lines),
            "googlebot_hits_count": len(self.googlebot_hits),
            "bingbot_hits_count": len(self.bingbot_hits),
            "other_hits_count": len(self.other_hits)
        }

    def calculate_crawl_frequency(self) -> Dict[str, Dict[str, int]]:
        """
        Calculates crawl frequency per URL for Googlebot and Bingbot.
        """
        frequency = defaultdict(lambda: {"googlebot": 0, "bingbot": 0, "total": 0})
        
        for hit in self.googlebot_hits:
            url = hit.get("url", "")
            frequency[url]["googlebot"] += 1
            frequency[url]["total"] += 1
            
        for hit in self.bingbot_hits:
            url = hit.get("url", "")
            frequency[url]["bingbot"] += 1
            frequency[url]["total"] += 1
            
        # Convert to standard dict
        return dict(frequency)

    def detect_crawl_traps(self) -> Dict[str, List[str]]:
        """
        Identifies potential crawl traps based on URL patterns from crawled hits:
        - URLs with 3+ query parameters
        - URLs with deep folder structure (5+ subfolders)
        - Infinite redirect loop indicators (status 301/302/307 with same path structure)
        """
        traps = {
            "excessive_params": [],
            "deep_paths": [],
            "potential_loops": []
        }
        
        seen_paths = defaultdict(int)
        
        all_bot_hits = self.googlebot_hits + self.bingbot_hits
        for hit in all_bot_hits:
            url = hit.get("url", "")
            status = hit.get("status", "200")
            parsed = urlparse(url)
            
            # 1. Check excessive query parameters (>= 3)
            params = parse_qs(parsed.query)
            if len(params) >= 3:
                if url not in traps["excessive_params"]:
                    traps["excessive_params"].append(url)
                    
            # 2. Check deep paths (>= 5 folders)
            path_parts = [p for p in parsed.path.split('/') if p]
            if len(path_parts) >= 5:
                if url not in traps["deep_paths"]:
                    traps["deep_paths"].append(url)
                    
            # 3. Track redirects to identify loops
            if status in ("301", "302", "307"):
                seen_paths[parsed.path] += 1
                if seen_paths[parsed.path] > 10:  # Excessive redirect hits for the same path
                    if url not in traps["potential_loops"]:
                        traps["potential_loops"].append(url)
                        
        return traps

    def generate_recommendations(self) -> List[str]:
        """
        Generates automated robots.txt or canonical fixes based on log data.
        """
        traps = self.detect_crawl_traps()
        recommendations = []
        
        if traps["excessive_params"]:
            recommendations.append(
                "Warning: Potential query parameter crawl traps detected. "
                "Recommendation: Add Disallow rules in robots.txt for filter parameters (e.g. Disallow: /*?*filter=)."
            )
            
        if traps["deep_paths"]:
            recommendations.append(
                "Warning: Extremely deep path levels detected in bot crawl history. "
                "Recommendation: Configure canonical tags to point to parent landing pages or Disallow deep nesting in robots.txt."
            )
            
        if traps["potential_loops"]:
            recommendations.append(
                "Critical: Potential infinite redirection loops detected. "
                "Recommendation: Review server redirect rules for loops or implement canonical loops resolution."
            )
            
        if not recommendations:
            recommendations.append("Crawl health is excellent. No crawl traps or bottlenecks detected in log history.")
            
        return recommendations
