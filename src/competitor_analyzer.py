import json
import math
import os
import re
import logging
from typing import Dict, List, Any, Optional, Set
from urllib.parse import urlparse
from collections import Counter

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    logging.warning("requests and bs4 are required for full functionality of CompetitorAnalyzer.")

logger = logging.getLogger(__name__)

class CompetitorAnalyzer:
    """
    Comprehensive Competitor Analysis Module for the SEO/GEO Framework.
    Analyzes competitor web pages to identify content gaps, structural advantages,
    and optimization opportunities.
    """

    def __init__(self, user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", config: Optional[Dict[str, Any]] = None):
        self.user_agent = user_agent
        self.headers = {"User-Agent": self.user_agent}
        self.config = config or {}
        self.google_api_key = self.config.get("google_api_key") or os.getenv("GOOGLE_API_KEY")
        self.google_search_engine_id = (
            self.config.get("google_search_engine_id")
            or self.config.get("google_cx")
            or os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        )

    def _fetch_html(self, url: str) -> Optional[str]:
        """Helper method to fetch HTML content with retry."""
        for attempt in range(2):
            try:
                response = requests.get(url, headers=self.headers, timeout=12, allow_redirects=True)
                response.raise_for_status()
                return response.text
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout fetching {url} (attempt {attempt + 1})")
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error fetching {url}: {e}")
                break
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                break
        return None

    def analyze_competitor(self, url: str) -> Dict[str, Any]:
        """
        Full page analysis of a single competitor URL.
        """
        html = self._fetch_html(url)
        if not html:
            return {"url": url, "error": "Could not fetch content"}

        soup = BeautifulSoup(html, "html.parser")
        
        # Extract text for word count
        for script in soup(["script", "style"]):
            script.extract()
        text = soup.get_text(separator=' ')
        words = [w.lower() for w in re.findall(r'\b\w+\b', text)]
        word_count = len(words)

        # Extract headings
        headings = {
            "h1": [h.get_text(strip=True) for h in soup.find_all("h1")],
            "h2": [h.get_text(strip=True) for h in soup.find_all("h2")],
            "h3": [h.get_text(strip=True) for h in soup.find_all("h3")],
            "h4": [h.get_text(strip=True) for h in soup.find_all("h4")]
        }

        # Extract schemas
        schemas = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                schemas.append(json.loads(script.string))
            except (json.JSONDecodeError, TypeError):
                continue

        # Extract links
        parsed_url = urlparse(url)
        base_domain = parsed_url.netloc
        links = soup.find_all("a", href=True)
        internal_links = []
        external_links = []
        for link in links:
            href = link['href']
            if href.startswith('/') or base_domain in href:
                internal_links.append(href)
            elif href.startswith('http'):
                external_links.append(href)

        # Extract images
        images = soup.find_all("img")
        images_data = [{"src": img.get('src'), "alt": img.get('alt', '')} for img in images]

        return {
            "url": url,
            "title": soup.title.string if soup.title else "",
            "meta_description": soup.find("meta", attrs={"name": "description"}).get("content") if soup.find("meta", attrs={"name": "description"}) else "",
            "word_count": word_count,
            "words": words, # Kept for keyword density, but might be large
            "headings": headings,
            "schemas": schemas,
            "internal_links_count": len(internal_links),
            "external_links_count": len(external_links),
            "images": images_data,
            "image_count": len(images_data),
            "images_with_alt": sum(1 for img in images_data if img["alt"])
        }

    def analyze_competitors(self, competitors: List[str], keyword: str = "") -> Dict[str, Any]:
        """Bulk competitor analysis — scrapes real pages with fallback to minimal stub."""
        analyses = []
        for url in competitors:
            try:
                result = self.analyze_competitor(url)
                analyses.append(result)
            except Exception as e:
                logger.warning(f"Failed to analyze {url}: {e}")
                # Minimal fallback so the report still includes this URL
                analyses.append({
                    "url": url,
                    "error": str(e),
                    "title": url,
                    "word_count": 0,
                    "words": [],
                    "headings": {"h1": [], "h2": [], "h3": [], "h4": []},
                    "schemas": [],
                    "internal_links_count": 0,
                    "external_links_count": 0,
                    "images": [],
                    "image_count": 0,
                    "images_with_alt": 0,
                })
        return self.get_competitor_report(analyses, target_keyword=keyword)

    def analyze_content_length(self, competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Word count comparison across competitors.
        """
        word_counts = [comp.get("word_count", 0) for comp in competitors if "error" not in comp]
        if not word_counts:
            return {}

        return {
            "average_word_count": sum(word_counts) / len(word_counts),
            "max_word_count": max(word_counts),
            "min_word_count": min(word_counts),
            "median_word_count": sorted(word_counts)[len(word_counts) // 2],
            "competitor_lengths": {comp["url"]: comp.get("word_count", 0) for comp in competitors if "error" not in comp}
        }

    def analyze_keyword_usage(self, competitors: List[Dict[str, Any]], keyword: str) -> Dict[str, Any]:
        """
        Keyword density and usage analysis.
        """
        keyword_lower = keyword.lower()
        keyword_tokens = keyword_lower.split()
        results = {}

        for comp in competitors:
            if "error" in comp:
                continue
            
            words = comp.get("words", [])
            total_words = comp.get("word_count", 0)
            if total_words == 0:
                continue

            # Exact match count (simple approximation)
            text_str = " ".join(words)
            exact_matches = text_str.count(keyword_lower)
            density = (exact_matches * len(keyword_tokens) / total_words) * 100 if total_words > 0 else 0

            in_title = keyword_lower in str(comp.get("title", "")).lower()
            in_h1 = any(keyword_lower in h.lower() for h in comp.get("headings", {}).get("h1", []))

            results[comp["url"]] = {
                "exact_matches": exact_matches,
                "density_percentage": round(density, 2),
                "in_title": in_title,
                "in_h1": in_h1
            }

        return results

    def analyze_heading_structure(self, competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        H2/H3 analysis to find common structural patterns.
        """
        all_h2s = []
        all_h3s = []
        structure_map = {}

        for comp in competitors:
            if "error" in comp:
                continue
            h2s = comp.get("headings", {}).get("h2", [])
            h3s = comp.get("headings", {}).get("h3", [])
            
            all_h2s.extend([h.lower() for h in h2s])
            all_h3s.extend([h.lower() for h in h3s])
            
            structure_map[comp["url"]] = {
                "h2_count": len(h2s),
                "h3_count": len(h3s),
                "h2s": h2s
            }

        # Find common topics in headings
        h2_counter = Counter(all_h2s)
        common_h2s = {h: count for h, count in h2_counter.items() if count > 1}

        return {
            "average_h2_count": sum(m["h2_count"] for m in structure_map.values()) / len(structure_map) if structure_map else 0,
            "common_h2_topics": common_h2s,
            "competitor_structures": structure_map
        }

    def analyze_schema_usage(self, competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Identifies JSON-LD Schema types used by competitors.
        """
        schema_types = Counter()
        competitor_schemas = {}

        for comp in competitors:
            if "error" in comp:
                continue
            types_found = set()
            for schema_block in comp.get("schemas", []):
                # Handle both dict and list of dicts
                blocks = schema_block if isinstance(schema_block, list) else [schema_block]
                for item in blocks:
                    if isinstance(item, dict) and "@type" in item:
                        t = item["@type"]
                        # Type can be string or list
                        if isinstance(t, list):
                            types_found.update(t)
                        else:
                            types_found.add(t)
            
            competitor_schemas[comp["url"]] = list(types_found)
            for t in types_found:
                schema_types[t] += 1

        return {
            "most_common_schemas": dict(schema_types.most_common()),
            "competitor_schema_map": competitor_schemas
        }

    def analyze_internal_links(self, competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Internal linking patterns.
        """
        return {
            comp["url"]: {"internal_links": comp.get("internal_links_count", 0)}
            for comp in competitors if "error" not in comp
        }

    def analyze_external_links(self, competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Outbound linking patterns.
        """
        return {
            comp["url"]: {"external_links": comp.get("external_links_count", 0)}
            for comp in competitors if "error" not in comp
        }

    def analyze_images(self, competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Image optimization (count and alt text usage).
        """
        results = {}
        for comp in competitors:
            if "error" in comp:
                continue
            total = comp.get("image_count", 0)
            with_alt = comp.get("images_with_alt", 0)
            results[comp["url"]] = {
                "total_images": total,
                "images_with_alt": with_alt,
                "alt_optimization_percentage": (with_alt / total * 100) if total > 0 else 0
            }
        return results

    def analyze_page_speed(self, competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Speed comparison (Requires Google PageSpeed API integration).
        Currently returns placeholder structure.
        """
        # Placeholder for external API call
        return {
            comp["url"]: {"simulated_speed_index": "N/A", "note": "Requires PageSpeed API integration"}
            for comp in competitors if "error" not in comp
        }

    def analyze_backlinks(self, url: str) -> Dict[str, Any]:
        """
        Backlink profile analysis (requires dedicated backlink APIs for full fidelity).
        Currently returns placeholder structure.
        """
        return {
            "url": url,
            "total_backlinks": "N/A",
            "referring_domains": "N/A",
            "domain_authority": "N/A",
            "note": "Requires backlink data provider integration (Ahrefs/Majestic or GSC link exports)."
        }

    def identify_content_gaps(self, competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Identifies missing topics by looking at common headings that appear across
        multiple competitors.
        """
        heading_analysis = self.analyze_heading_structure(competitors)
        common_topics = heading_analysis.get("common_h2_topics", {})
        
        # Identify gaps per competitor
        gaps = {}
        for comp in competitors:
            if "error" in comp:
                continue
            comp_h2s = [h.lower() for h in comp.get("headings", {}).get("h2", [])]
            missing = [topic for topic in common_topics.keys() if topic not in comp_h2s]
            gaps[comp["url"]] = missing

        return {
            "high_value_topics": list(common_topics.keys()),
            "competitor_gaps": gaps
        }

    def identify_keyword_gaps(self, competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Identifies missing keywords (Approximated by TF-IDF / common bigrams in a real system).
        """
        # A simple heuristic extracting common words excluding stop words
        stop_words = {"the", "and", "a", "to", "of", "in", "i", "is", "that", "it", "on", "you", "this", "for", "with", "are"}
        all_words_counter = Counter()
        
        comp_vocab = {}
        for comp in competitors:
            if "error" in comp:
                continue
            words = [w for w in comp.get("words", []) if len(w) > 3 and w not in stop_words]
            vocab = set(words)
            comp_vocab[comp["url"]] = vocab
            for w in vocab:
                all_words_counter[w] += 1
                
        # Words used by at least 2 competitors
        core_keywords = {w for w, c in all_words_counter.items() if c > 1}
        
        gaps = {}
        for url, vocab in comp_vocab.items():
            gaps[url] = list(core_keywords - vocab)[:20] # Top 20 missing

        return {
            "core_market_keywords": list(core_keywords)[:50],
            "gaps_per_competitor": gaps
        }

    def identify_entity_gaps(self, competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Identifies missing named entities (Requires NLP like SpaCy for exactness).
        Using simple capitalized word extraction as a fallback heuristic.
        """
        all_entities = Counter()
        comp_entities = {}

        for comp in competitors:
            if "error" in comp:
                continue
            text = " ".join(comp.get("words", []))
            # Rough heuristic for capitalized phrases (Entities)
            # In production, use standard NER (Named Entity Recognition)
            entities = set(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text))
            comp_entities[comp["url"]] = entities
            for e in entities:
                all_entities[e] += 1

        common_entities = {e for e, c in all_entities.items() if c > 1}
        
        gaps = {}
        for url, entities in comp_entities.items():
            gaps[url] = list(common_entities - entities)[:20]

        return {
            "common_entities": list(common_entities)[:50],
            "gaps_per_competitor": gaps
        }

    def calculate_competitiveness_score(self, keyword: str) -> Dict[str, Any]:
        """
        Estimates the difficulty of a keyword.
        """
        if self.google_api_key and self.google_search_engine_id:
            try:
                try:
                    from src.apis.google_custom_search import GoogleCustomSearchAPI
                except ImportError:
                    from apis.google_custom_search import GoogleCustomSearchAPI

                api = GoogleCustomSearchAPI(
                    api_key=self.google_api_key,
                    search_engine_id=self.google_search_engine_id,
                )
                meta = api.get_search_metadata(keyword)
                total_results = int(str(meta.get("total_results", "0")).replace(",", ""))
                kd = max(5, min(95, int(math.log10(total_results + 1) * 12.5)))
                return {
                    "keyword": keyword,
                    "competitiveness_score": float(kd),
                    "difficulty_rating": "High" if kd > 75 else ("Medium" if kd > 40 else "Low"),
                    "note": "Powered by Google Custom Search API",
                }
            except Exception as e:
                logger.error(f"Error calling Google Custom Search API: {str(e)}")

        # Fallback algorithm when no API key is present
        return {
            "keyword": keyword,
            "competitiveness_score": 65, # 0-100 scale
            "difficulty_rating": "Medium-High",
            "note": "Set GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID for live competitiveness estimation."
        }

    def get_competitor_report(self, competitors: List[Dict[str, Any]], target_keyword: str = "") -> Dict[str, Any]:
        """
        Generates a comprehensive report running all analysis modules.
        """
        if not competitors:
            return {"error": "No competitors provided"}

        report = {
            "summary": {
                "competitors_analyzed": len([c for c in competitors if "error" not in c])
            },
            "content_length": self.analyze_content_length(competitors),
            "heading_structure": self.analyze_heading_structure(competitors),
            "schema_usage": self.analyze_schema_usage(competitors),
            "links": {
                "internal": self.analyze_internal_links(competitors),
                "external": self.analyze_external_links(competitors)
            },
            "images": self.analyze_images(competitors),
            "gaps": {
                "content": self.identify_content_gaps(competitors),
                "keywords": self.identify_keyword_gaps(competitors),
                "entities": self.identify_entity_gaps(competitors)
            }
        }

        if target_keyword:
            report["keyword_usage"] = self.analyze_keyword_usage(competitors, target_keyword)
            report["competitiveness"] = self.calculate_competitiveness_score(target_keyword)

        return report
