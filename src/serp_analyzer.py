import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

try:
    from .integrations.duckduckgo_client import DuckDuckGoClient
except ImportError:
    try:
        from integrations.duckduckgo_client import DuckDuckGoClient
    except ImportError:
        DuckDuckGoClient = None

logger = logging.getLogger(__name__)

class SERPAnalyzer:
    """
    Comprehensive SERP (Search Engine Results Page) Analysis Module.
    Integrates multiple data sources (Google Custom Search, Brave, Tavily, Perplexity, GLM, Playwright)
    to perform deep analysis of search results for SEO/GEO framework.
    """

    def __init__(self):
        self.google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_CUSTOM_SEARCH_KEY")
        self.cx = os.getenv("GOOGLE_CX") or os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        self.brave_api_key = os.getenv("BRAVE_SEARCH_API_KEY")
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        self.glm_api_key = os.getenv("GLM_API_KEY")
        self.google_search = bool(self.google_api_key and self.cx)
        
        # Ensure tracking directory exists
        self.history_dir = os.path.join(os.getcwd(), ".ai", "artifacts", "serp_history")
        os.makedirs(self.history_dir, exist_ok=True)

    def search(self, keyword: str, location: str = "United States", device: str = "desktop") -> Dict[str, Any]:
        """Compatibility alias for older callers."""
        return self.analyze_serp(keyword=keyword, location=location, device=device)

    def analyze_serp(self, keyword: str, location: str = "United States", device: str = "desktop", limit: int | None = None) -> Dict[str, Any]:
        """
        Executes a full SERP analysis combining all available data and insights.
        When limit is provided, runs a lightweight analysis (DuckDuckGo or API-based).
        """
        logger.info(f"Starting SERP analysis for '{keyword}' ({location}, {device}), limit={limit}")
        
        # 1. Fetch raw SERP layout
        raw_serp_data = self._fetch_raw_serp(keyword, location, device)
        
        # 2. Extract specific SERP features
        organic_results = self.extract_organic_results(raw_serp_data)
        
        analysis_result = {
            "keyword": keyword,
            "location": location,
            "device": device,
            "timestamp": datetime.now().isoformat(),
            "organic_results": organic_results,
            "featured_snippets": self.extract_featured_snippets(raw_serp_data),
            "paa_questions": self.extract_paa_questions(raw_serp_data),
            "related_searches": self.extract_related_searches(raw_serp_data),
            "knowledge_panel": self.extract_knowledge_panel(raw_serp_data),
            "local_pack": self.extract_local_pack(raw_serp_data),
            "image_pack": self.extract_image_pack(raw_serp_data),
            "video_results": self.extract_video_results(raw_serp_data),
        }
        
        # 3. Deep dive into competitor content
        top_urls = [res.get("link") for res in organic_results[:10] if res.get("link")]
        competitor_content = self.analyze_competitor_content(top_urls)
        analysis_result["competitor_analysis"] = competitor_content
        
        # 4. Derived metrics
        analysis_result["keyword_difficulty"] = self.calculate_keyword_difficulty(analysis_result)
        analysis_result["content_gaps"] = self.identify_content_gaps(keyword, competitor_content)
        
        # 5. Historical tracking
        self.track_serp_changes(keyword, analysis_result)
        
        return analysis_result

    def extract_paa(self, keyword: str) -> List[Dict[str, str]]:
        """Compatibility helper returning PAA questions for a keyword."""
        analysis = self.analyze_serp(keyword)
        return analysis.get("paa_questions", [])

    def _fetch_raw_serp(self, keyword: str, location: str, device: str) -> Dict[str, Any]:
        """
        Fetches raw SERP data prioritizing Google Custom Search -> Brave -> Tavily -> Perplexity -> GLM.
        """
        if self.google_api_key and self.cx:
            return self._fetch_via_gcs(keyword)
        elif self.brave_api_key:
            return self._fetch_via_brave(keyword, location)
        elif self.tavily_api_key:
            return self._fetch_via_tavily(keyword)
        elif self.perplexity_api_key:
            return self._fetch_via_perplexity(keyword)
        elif self.glm_api_key:
            return self._fetch_via_glm(keyword)
        else:
            # Fallback to DuckDuckGo (free, no API key required)
            return self._fetch_via_duckduckgo(keyword)

    def _fetch_via_brave(self, keyword: str, location: str) -> Dict[str, Any]:
        url = "https://api.search.brave.com/res/v1/web/search"
        params = {
            "q": keyword,
            "country": (location[:2] if location else "us").upper(),
            "count": 20,
        }
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.brave_api_key,
        }
        try:
            response = requests.get(url, params=params, headers=headers, timeout=20)
            if response.status_code == 200:
                raw = response.json()
                results = []
                for idx, item in enumerate(raw.get("web", {}).get("results", []), 1):
                    results.append(
                        {
                            "position": idx,
                            "title": item.get("title", ""),
                            "link": item.get("url", ""),
                            "snippet": item.get("description", ""),
                            "displayed_link": item.get("url", ""),
                        }
                    )
                return {"organic_results": results}
        except Exception as e:
            logger.error(f"Brave Search fetch failed: {e}")
        return {}

    def _fetch_via_tavily(self, keyword: str) -> Dict[str, Any]:
        url = "https://api.tavily.com/search"
        payload = {"api_key": self.tavily_api_key, "query": keyword, "max_results": 10, "search_depth": "basic"}
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                raw = response.json()
                results = []
                for idx, item in enumerate(raw.get("results", []), 1):
                    results.append(
                        {
                            "position": idx,
                            "title": item.get("title", ""),
                            "link": item.get("url", ""),
                            "snippet": item.get("content", ""),
                            "displayed_link": item.get("url", ""),
                        }
                    )
                return {"organic_results": results}
        except Exception as e:
            logger.error(f"Tavily fetch failed: {e}")
        return {}

    def _fetch_via_gcs(self, keyword: str) -> Dict[str, Any]:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.google_api_key,
            "cx": self.cx,
            "q": keyword,
            "num": 10 # GCS max is 10
        }
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return {"organic_results": data.get("items", [])}
        except Exception as e:
            logger.error(f"Google Custom Search fetch failed: {e}")
        return {}

    def _fetch_via_perplexity(self, keyword: str) -> Dict[str, Any]:
        url = "https://api.perplexity.ai/chat/completions"
        headers = {"Authorization": f"Bearer {self.perplexity_api_key}"}
        payload = {
            "model": "sonar",
            "messages": [
                {"role": "system", "content": "Return concise web-grounded search summary."},
                {"role": "user", "content": f"Top search findings for query: {keyword}"},
            ],
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            if response.status_code == 200:
                raw = response.json()
                text = (
                    raw.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                return {
                    "organic_results": [
                        {
                            "position": 1,
                            "title": f"{keyword} summary",
                            "link": "",
                            "snippet": text,
                            "displayed_link": "",
                        }
                    ]
                }
        except Exception as e:
            logger.error(f"Perplexity fetch failed: {e}")
        return {}

    def _fetch_via_glm(self, keyword: str) -> Dict[str, Any]:
        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        headers = {"Authorization": f"Bearer {self.glm_api_key}"}
        payload = {
            "model": "glm-4.5",
            "tools": [{"type": "web_search"}],
            "messages": [{"role": "user", "content": f"Top search findings for query: {keyword}"}],
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            if response.status_code == 200:
                raw = response.json()
                text = (
                    raw.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                return {
                    "organic_results": [
                        {
                            "position": 1,
                            "title": f"{keyword} summary",
                            "link": "",
                            "snippet": text,
                            "displayed_link": "",
                        }
                    ]
                }
        except Exception as e:
            logger.error(f"GLM fetch failed: {e}")
        return {}

    def _fetch_via_duckduckgo(self, keyword: str) -> Dict[str, Any]:
        """Fetch real web search data via DuckDuckGo (free, no key required).

        Uses the ddgs package for actual web search results instead of
        the limited Instant Answer API.
        """
        if DuckDuckGoClient is None:
            logger.warning("DuckDuckGoClient not available. Returning empty results.")
            return {"organic_results": [], "related_topics": []}

        try:
            client = DuckDuckGoClient()

            # Get web search results (sync call)
            raw_results = client.search_sync(keyword, max_results=15, region="uk-en")

            # Convert to standard organic_results format
            organic_results = []
            for idx, r in enumerate(raw_results, 1):
                organic_results.append({
                    "position": idx,
                    "title": r.get("title", ""),
                    "link": r.get("href", ""),
                    "snippet": r.get("body", ""),
                    "displayed_link": r.get("href", ""),
                })

            # Get search suggestions as related searches
            suggestions = client.get_suggestions(keyword, region="uk-en")
            related_searches = [{"query": s} for s in suggestions[:10]]

            # Build PAA-like questions from suggestions
            paa_questions = []
            question_words = ("what", "how", "why", "when", "where", "which", "can", "do", "does", "is", "are")
            for s in suggestions:
                s_lower = s.lower()
                if any(s_lower.startswith(qw) for qw in question_words):
                    paa_questions.append({
                        "question": s,
                        "snippet": "",
                        "title": "",
                        "link": "",
                    })

            # If no natural questions found, generate from keyword + suggestions
            if not paa_questions:
                paa_questions = [
                    {"question": f"How much does {keyword} cost?", "snippet": "", "title": "", "link": ""},
                    {"question": f"What is {keyword}?", "snippet": "", "title": "", "link": ""},
                    {"question": f"How long does {keyword} take?", "snippet": "", "title": "", "link": ""},
                ]

            return {
                "organic_results": organic_results,
                "related_questions": paa_questions,
                "related_searches": related_searches,
                "answer_box": {},
                "source": "duckduckgo_web",
            }

        except Exception as e:
            logger.error(f"DuckDuckGo fetch failed: {e}")
            return {"organic_results": [], "related_topics": []}

    def extract_organic_results(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extracts the top 100 organic search results."""
        results = raw_data.get("organic_results", [])
        return [{
            "position": res.get("position", idx + 1),
            "title": res.get("title", ""),
            "link": res.get("link", ""),
            "snippet": res.get("snippet", ""),
            "displayed_link": res.get("displayed_link", "")
        } for idx, res in enumerate(results)]

    def extract_featured_snippets(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts all featured snippet types (paragraphs, lists, tables)."""
        snippet = raw_data.get("answer_box", raw_data.get("featured_snippet", {}))
        if not snippet:
            return {}
        return {
            "type": snippet.get("type", "unknown"),
            "title": snippet.get("title", ""),
            "link": snippet.get("link", ""),
            "snippet": snippet.get("snippet", snippet.get("answer", "")),
            "list": snippet.get("list", []),
            "table": snippet.get("table", [])
        }

    def extract_paa_questions(self, raw_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extracts People Also Ask (PAA) questions and their snippet answers."""
        paa = raw_data.get("related_questions", [])
        return [{
            "question": item.get("question", ""),
            "snippet": item.get("snippet", ""),
            "title": item.get("title", ""),
            "link": item.get("link", "")
        } for item in paa]

    def extract_related_searches(self, raw_data: Dict[str, Any]) -> List[str]:
        """Extracts related search queries from the bottom of the SERP."""
        related = raw_data.get("related_searches", [])
        return [item.get("query", "") for item in related if "query" in item]

    def extract_knowledge_panel(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts Knowledge Graph panel data."""
        kg = raw_data.get("knowledge_graph", {})
        if not kg:
            return {}
        return {
            "title": kg.get("title", ""),
            "type": kg.get("type", ""),
            "description": kg.get("description", ""),
            "website": kg.get("website", ""),
            "attributes": {k: v for k, v in kg.items() if k not in ["title", "type", "description", "website"]}
        }

    def extract_local_pack(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extracts local 3-pack or map results."""
        return raw_data.get("local_results", raw_data.get("places", []))

    def extract_image_pack(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extracts image carousel results."""
        return raw_data.get("inline_images", raw_data.get("images_results", []))

    def extract_video_results(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extracts video carousel results."""
        return raw_data.get("inline_videos", raw_data.get("video_results", []))

    def analyze_competitor_content(self, urls: List[str]) -> Dict[str, Any]:
        """
        Analyzes the top 10 organic results. Prioritizes Playwright for JS-rendered 
        content, falls back to requests + BeautifulSoup.
        """
        analysis = {}
        
        # Try Playwright if available
        if sync_playwright:
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                    
                    for url in urls[:10]:
                        try:
                            page = context.new_page()
                            page.goto(url, timeout=15000, wait_until="domcontentloaded")
                            
                            headings = page.evaluate('''() => {
                                return Array.from(document.querySelectorAll('h1, h2, h3')).map(h => ({
                                    tag: h.tagName.toLowerCase(),
                                    text: h.innerText.trim()
                                })).filter(h => h.text.length > 0);
                            }''')
                            
                            text_content = page.evaluate('document.body.innerText')
                            word_count = len(text_content.split())
                            
                            analysis[url] = {
                                "word_count": word_count,
                                "headings": headings,
                                "title": page.title(),
                                "scraped_via": "playwright"
                            }
                            page.close()
                        except Exception as e:
                            logger.error(f"Playwright failed for {url}: {e}")
                            analysis[url] = {"error": str(e)}
                            
                    browser.close()
            except Exception as e:
                logger.error(f"Playwright execution failed: {e}. Falling back to requests.")
        
        # Fallback to requests + BS4 for URLs that failed or if Playwright is missing
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
        for url in urls[:10]:
            if url not in analysis or "error" in analysis[url]:
                try:
                    resp = requests.get(url, timeout=10, headers=headers)
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    
                    headings = [
                        {"tag": h.name, "text": h.get_text(strip=True)} 
                        for h in soup.find_all(['h1', 'h2', 'h3']) if h.get_text(strip=True)
                    ]
                    
                    # Remove script and style elements before counting words
                    for script in soup(["script", "style"]):
                        script.decompose()
                        
                    word_count = len(soup.get_text(separator=' ').split())
                    
                    analysis[url] = {
                        "word_count": word_count,
                        "headings": headings,
                        "title": soup.title.string if soup.title else "",
                        "scraped_via": "beautifulsoup"
                    }
                except Exception as e:
                    logger.error(f"Fallback scraping failed for {url}: {e}")
                    if url not in analysis:
                        analysis[url] = {"error": str(e)}

        return analysis

    def analyze_competitors(self, urls: List[str]) -> Dict[str, Any]:
        """Compatibility alias for tests expecting analyze_competitors."""
        return self.analyze_competitor_content(urls)

    def calculate_keyword_difficulty(self, serp_data: Dict[str, Any]) -> int:
        """
        Calculates a proprietary keyword difficulty score (0-100) based on SERP features
        and competitor content depth.
        """
        score = 50 # Base score
        
        # Increase difficulty if SERP is crowded with rich features
        if serp_data.get("featured_snippets"): score += 10
        if serp_data.get("knowledge_panel"): score += 15
        if serp_data.get("local_pack"): score += 10
        if serp_data.get("video_results"): score += 5
        
        # Analyze competitor word counts (longer content implies higher difficulty)
        competitors = serp_data.get("competitor_analysis", {})
        valid_counts = [data.get("word_count", 0) for data in competitors.values() if data.get("word_count")]
        
        if valid_counts:
            avg_word_count = sum(valid_counts) / len(valid_counts)
            if avg_word_count > 3000: score += 15
            elif avg_word_count > 2000: score += 10
            elif avg_word_count > 1000: score += 5
            elif avg_word_count < 500: score -= 10
            
        # Ensure bounds
        return max(0, min(100, int(score)))

    def identify_content_gaps(self, keyword: str, competitor_data: Dict[str, Any]) -> List[str]:
        """
        Identifies missing topics (content gaps) by analyzing competitor headings
        and comparing them against the target keyword.
        """
        all_headings = []
        for url, data in competitor_data.items():
            if "headings" in data:
                all_headings.extend([h.get("text", "").lower() for h in data["headings"]])
                
        # Simple frequency analysis of words in headings, excluding the main keyword
        keyword_parts = set(keyword.lower().split())
        word_freq = {}
        
        for heading in all_headings:
            words = set(heading.split())
            for word in words:
                if len(word) > 4 and word not in keyword_parts: # Basic filter
                    word_freq[word] = word_freq.get(word, 0) + 1
                    
        # Sort by frequency
        sorted_gaps = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        # Return top 10 potential topic gaps
        return [word for word, count in sorted_gaps[:10]]

    def get_competitor_gaps(self, keyword: str, competitor_data: Dict[str, Any]) -> List[str]:
        """Alias for identify_content_gaps to maintain test compatibility."""
        return self.identify_content_gaps(keyword, competitor_data)

    def track_serp_changes(self, keyword: str, current_serp: Dict[str, Any]):
        """
        Saves the current SERP analysis to track historical changes.
        """
        safe_keyword = "".join(x for x in keyword if x.isalnum() or x in " -_").replace(" ", "_")
        filename = f"{safe_keyword}_history.json"
        filepath = os.path.join(self.history_dir, filename)
        
        history = []
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except Exception as e:
                logger.error(f"Failed to read history for {keyword}: {e}")
                
        # Append minimal summary to history to save space
        summary = {
            "timestamp": current_serp["timestamp"],
            "difficulty": current_serp["keyword_difficulty"],
            "top_3_urls": [res.get("link") for res in current_serp["organic_results"][:3]],
            "has_snippet": bool(current_serp["featured_snippets"])
        }
        
        history.append(summary)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2)
            logger.info(f"SERP history updated for '{keyword}'")
        except Exception as e:
            logger.error(f"Failed to write history for {keyword}: {e}")
