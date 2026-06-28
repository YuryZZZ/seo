"""
Backlink Analyzer Module for SEO/GEO Framework
Uses Google Custom Search and Brave Search APIs for backlink/mention proxy tracking.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json

logger = logging.getLogger(__name__)

@dataclass
class BacklinkData:
    """Data class for backlink information"""
    source_url: str
    target_url: str
    anchor_text: str
    domain_rating: Optional[float] = None
    url_rating: Optional[float] = None
    traffic: Optional[int] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    dofollow: bool = True
    link_type: str = "text"  # text, image, redirect
    
class BacklinkAnalyzer:
    """Backlink analyzer using approved search providers."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the backlink analyzer with API configurations.
        
        Args:
            config: Dictionary containing API keys and configurations
                   Expected keys: google_api_key, google_search_engine_id, brave_api_key
        """
        self.config = config or {}
        self.google_api_key = self.config.get("google_api_key")
        self.google_search_engine_id = self.config.get("google_search_engine_id") or self.config.get("google_cx")
        self.brave_api_key = self.config.get("brave_api_key")
        
        # Initialize API clients
        self._init_clients()
        
    def _init_clients(self):
        """Initialize API clients based on available keys"""
        self.clients = {}

        if self.google_api_key and self.google_search_engine_id:
            self.clients["google_search"] = self._init_google_search_client()

        if self.brave_api_key:
            self.clients["brave_search"] = self._init_brave_search_client()
            
        logger.info(f"Initialized backlink analyzer with clients: {list(self.clients.keys())}")
    
    def _init_google_search_client(self):
        """Initialize Google Custom Search client for lightweight domain mention estimates."""
        try:
            from src.api.google_search_client import GoogleSearchClient

            logger.info("Google Search: Initializing Google Custom Search client")

            class GoogleSearchAdapter:
                def __init__(self, api_key: str, search_engine_id: str):
                    self.api = GoogleSearchClient(api_key=api_key, search_engine_id=search_engine_id)

                def get_backlink_proxy(self, domain: str) -> Dict[str, Any]:
                    query = f'"{domain}" -site:{domain}'
                    meta = self.api.get_search_metadata(query)
                    total_mentions = int(str(meta.get("total_results", "0")).replace(",", ""))
                    # Proxy heuristics: mentions are broader than links.
                    estimated_referring_domains = max(0, min(50000, total_mentions // 25))
                    estimated_backlinks = max(0, min(5000000, total_mentions // 5))
                    return {
                        "google_mentions_estimate": total_mentions,
                        "referring_domains_estimate": estimated_referring_domains,
                        "total_backlinks_estimate": estimated_backlinks,
                    }

            return GoogleSearchAdapter(self.google_api_key, self.google_search_engine_id)
        except Exception as e:
            logger.warning("Google Search client init failed: %s", e)
            return None

    def _init_brave_search_client(self):
        """Initialize Brave Search client for mention/ref-domain proxy estimates."""
        try:
            import requests

            logger.info("Brave Search: Initializing client")

            class BraveSearchAdapter:
                def __init__(self, api_key: str):
                    self.api_key = api_key

                def get_backlink_proxy(self, domain: str) -> Dict[str, Any]:
                    headers = {
                        "Accept": "application/json",
                        "X-Subscription-Token": self.api_key,
                    }
                    params = {"q": f'"{domain}" -site:{domain}', "count": 20}
                    response = requests.get(
                        "https://api.search.brave.com/res/v1/web/search",
                        headers=headers,
                        params=params,
                        timeout=20,
                    )
                    response.raise_for_status()
                    data = response.json()
                    web_results = data.get("web", {}).get("results", [])
                    mentions = len(web_results) * 1000
                    return {
                        "brave_mentions_estimate": mentions,
                        "brave_referring_domains_estimate": max(0, min(50000, mentions // 30)),
                    }

            return BraveSearchAdapter(self.brave_api_key)
        except Exception as e:
            logger.warning("Brave Search client init failed: %s", e)
            return None
    
    def analyze_domain(self, domain: str) -> Dict[str, Any]:
        """
        Perform comprehensive backlink analysis for a domain.
        
        Args:
            domain: Domain to analyze (e.g., 'example.com')
            
        Returns:
            Dictionary containing backlink analysis results
        """
        logger.info(f"Starting backlink analysis for domain: {domain}")
        
        results = {
            'domain': domain,
            'timestamp': datetime.now().isoformat(),
            'backlinks': [],
            'metrics': {},
            'recommendations': []
        }
        
        # Collect data from approved APIs
        if 'google_search' in self.clients and self.clients['google_search'] is not None:
            try:
                google_data = self.clients['google_search'].get_backlink_proxy(domain)
                results['metrics'].update(google_data)
            except Exception as e:
                logger.error(f"Google Search API error: {e}")
                results['metrics']['google_search_error'] = str(e)

        if 'brave_search' in self.clients and self.clients['brave_search'] is not None:
            try:
                brave_data = self.clients['brave_search'].get_backlink_proxy(domain)
                results['metrics'].update(brave_data)
            except Exception as e:
                logger.error(f"Brave Search API error: {e}")
                results['metrics']['brave_search_error'] = str(e)
        
        # Generate recommendations based on analysis
        results['recommendations'] = self._generate_recommendations(results)
        
        logger.info(f"Completed backlink analysis for {domain}")
        return results

    def analyze_backlinks(self, domain: str) -> Dict[str, Any]:
        """Compatibility wrapper for tests expecting analyze_backlinks()."""
        return self.analyze_domain(domain)
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate SEO recommendations based on backlink analysis"""
        recommendations = []
        
        # Check if we have any backlinks
        if not analysis['backlinks']:
            recommendations.append("No backlinks found. Consider starting a backlink building campaign.")
            
        # Check domain authority metrics
        if 'domain_authority' in analysis['metrics']:
            da = analysis['metrics']['domain_authority']
            if da < 30:
                recommendations.append(f"Domain Authority ({da}) is low. Focus on quality content and authoritative backlinks.")
            elif da < 50:
                recommendations.append(f"Domain Authority ({da}) is moderate. Continue building quality backlinks.")
                
        # Check backlink diversity
        if len(analysis['backlinks']) > 0:
            unique_domains = len(set(bl.get('source_domain', '') for bl in analysis['backlinks']))
            if unique_domains < 10:
                recommendations.append(f"Low backlink diversity ({unique_domains} domains). Diversify your link sources.")
                
        return recommendations
    
    def export_analysis(self, analysis: Dict[str, Any], format: str = 'json') -> str:
        """
        Export analysis results in specified format.
        
        Args:
            analysis: Analysis results from analyze_domain()
            format: Output format ('json', 'csv', 'html')
            
        Returns:
            String containing formatted analysis
        """
        if format == 'json':
            return json.dumps(analysis, indent=2, default=str)
        elif format == 'csv':
            # Simple CSV export implementation
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['Domain', 'Timestamp', 'Metric', 'Value'])
            
            # Write metrics
            for key, value in analysis['metrics'].items():
                writer.writerow([analysis['domain'], analysis['timestamp'], key, value])
                
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")

    def get_domain_authority(self, domain: str) -> float:
        """Get domain authority score."""
        res = self.analyze_domain(domain)
        return float(res.get("metrics", {}).get("domain_authority", 30.0))
