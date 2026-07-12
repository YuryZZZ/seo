import re
import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

class ContentFreshnessAnalyzer:
    """
    Analyzes content for freshness, decay, and outdated information.
    Crucial for maintaining high SEO/GEO rankings by ensuring content remains current,
    accurate, and signals recent updates to search engines and AI models.
    """
    
    def __init__(self):
        # Using 2026 as the baseline since the system environment current date is 2026
        now = datetime.datetime.now()
        self.current_year = now.year if now.year >= 2026 else 2026
        self.current_date = now

    def analyze_content_age(self, content: str) -> Dict[str, Any]:
        """Analyzes the apparent age of the content based on date mentions."""
        years = [int(y) for y in re.findall(r'\b(19\d{2}|20\d{2})\b', content)]
        if not years:
            return {
                "apparent_age_years": 0, 
                "latest_year_mentioned": None, 
                "status": "evergreen_or_undated"
            }
        
        latest_year = max(years)
        age = self.current_year - latest_year
        
        status = "fresh"
        if age >= 3:
            status = "stale"
        elif age >= 1:
            status = "aging"

        return {
            "apparent_age_years": age,
            "latest_year_mentioned": latest_year,
            "all_years_mentioned": sorted(list(set(years))),
            "status": status
        }

    def check_freshness_signals(self, content: str) -> Dict[str, Any]:
        """Checks for explicit and implicit freshness signals in the text."""
        signals = {
            "has_current_year": str(self.current_year) in content,
            "has_recent_years": str(self.current_year - 1) in content or str(self.current_year - 2) in content,
            "temporal_words": len(re.findall(r'\b(recently|lately|this year|nowadays|currently|latest|new|updated)\b', content, re.IGNORECASE)),
            "outdated_words": len(re.findall(r'\b(formerly|in the past|used to|decade ago|years ago|previously)\b', content, re.IGNORECASE))
        }
        return signals

    def identify_outdated_content(self, content: str) -> List[str]:
        """Identifies potentially outdated sections, sentences, or references."""
        outdated_sentences = []
        # Split into sentences roughly
        sentences = re.split(r'(?<=[.!?]) +', content)
        
        # Stale year threshold (older than 2 years)
        stale_threshold = self.current_year - 2
        
        for sentence in sentences:
            years = [int(y) for y in re.findall(r'\b(19\d{2}|20\d{2})\b', sentence)]
            if any(y <= stale_threshold for y in years):
                outdated_sentences.append(sentence.strip())
            # Check for past future predictions (e.g., "will launch in 2024" when it's 2026)
            elif re.search(r'\b(is expected to|will launch in|upcoming in|planned for)\s+(201\d|202[0-5])\b', sentence, re.IGNORECASE):
                outdated_sentences.append(sentence.strip())
                
        return outdated_sentences

    def suggest_updates(self, content: str, topic: str = "") -> List[str]:
        """Provides specific update recommendations based on content analysis."""
        suggestions = []
        age_analysis = self.analyze_content_age(content)
        
        if age_analysis["status"] in ["stale", "aging"]:
            suggestions.append(f"Update references to past years. The latest year mentioned is {age_analysis['latest_year_mentioned']}, but the current year is {self.current_year}.")
        
        if not str(self.current_year) in content:
            suggestions.append(f"Add current year ({self.current_year}) context, statistics, or references to signal freshness to search engines.")
            
        outdated = self.identify_outdated_content(content)
        if outdated:
            suggestions.append(f"Review and update {len(outdated)} potentially outdated sentences containing old dates or past-tense future predictions.")
            
        stale_stats = self.detect_stale_statistics(content)
        if stale_stats:
            suggestions.append(f"Update {len(stale_stats)} statistics that appear to be from older sources.")

        if topic:
            suggestions.append(f"Consider adding a 'What's new in {self.current_year} for {topic}' section to modernize the content.")
            
        return suggestions

    def calculate_freshness_score(self, content: str) -> int:
        """Calculates a 0-100 freshness score based on signals and decay."""
        score = 100
        
        # Penalize for lack of current year
        if str(self.current_year) not in content:
            score -= 15
            
        age_analysis = self.analyze_content_age(content)
        if age_analysis["status"] == "stale":
            score -= 30
        elif age_analysis["status"] == "aging":
            score -= 15
            
        outdated_sections = self.identify_outdated_content(content)
        score -= min(30, len(outdated_sections) * 5)
        
        stale_stats = self.detect_stale_statistics(content)
        score -= min(20, len(stale_stats) * 5)
        
        signals = self.check_freshness_signals(content)
        if signals["temporal_words"] == 0:
            score -= 5
            
        if signals["outdated_words"] > 3:
            score -= min(10, signals["outdated_words"] * 2)
            
        return max(0, min(100, score))

    def track_content_decay(self, url: str) -> Dict[str, Any]:
        """
        Tracks how content decays over time.
        In a production environment, this integrates with Google Search Console or Analytics APIs
        to track CTR, impressions, and ranking drops.
        """
        # Simulated framework payload for decay tracking
        return {
            "url": url,
            "decay_status": "monitoring",
            "estimated_half_life_months": 18,
            "metrics_to_track": ["organic_traffic_30d", "ctr_variance", "keyword_position_drops"],
            "recommendation": "Integrate Search Console API to measure real-world impression decay."
        }

    def set_refresh_schedule(self, content: str, interval: str = "auto") -> Dict[str, Any]:
        """Determines automated refresh schedules for the content."""
        if interval == "auto":
            score = self.calculate_freshness_score(content)
            if score < 50:
                recommended_interval = "immediate"
                next_review = self.current_date
            elif score < 80:
                recommended_interval = "3_months"
                next_review = self.current_date + datetime.timedelta(days=90)
            else:
                recommended_interval = "6_months"
                next_review = self.current_date + datetime.timedelta(days=180)
        else:
            recommended_interval = interval
            days_map = {"1_month": 30, "3_months": 90, "6_months": 180, "1_year": 365}
            next_review = self.current_date + datetime.timedelta(days=days_map.get(interval, 180))
            
        return {
            "schedule_interval": recommended_interval,
            "next_review_date": next_review.strftime("%Y-%m-%d"),
            "automated_flag": True
        }

    def detect_stale_statistics(self, content: str) -> List[str]:
        """Finds outdated statistics (e.g. percentages, fractions tied to old years)."""
        stale_stats = []
        sentences = re.split(r'(?<=[.!?]) +', content)
        
        stale_year = self.current_year - 2 # Stats older than 2 years are considered stale
        
        # Look for % or "percent" near a year in the same sentence
        for sentence in sentences:
            if '%' in sentence or 'percent' in sentence.lower() or 'stat' in sentence.lower():
                years = [int(y) for y in re.findall(r'\b(19\d{2}|20\d{2})\b', sentence)]
                if any(y <= stale_year for y in years):
                    stale_stats.append(sentence.strip())
                    
        return stale_stats

    def detect_broken_links(self, content: str) -> List[Dict[str, str]]:
        """
        Identifies URLs in the content to check for link rot.
        Prepares them for an asynchronous HTTP verification queue.
        """
        # Find markdown links or raw hrefs
        markdown_links = re.findall(r'\]\((http[^\)]+)\)', content)
        href_links = re.findall(r'href=[\'"]?(http[^\'" >]+)', content)
        
        all_urls = list(set(markdown_links + href_links))
        results = []
        
        for url in all_urls:
            try:
                parsed = urlparse(url)
                status = "valid_format" if all([parsed.scheme, parsed.netloc]) else "invalid_format"
                results.append({
                    "url": url,
                    "status": status,
                    "validation_required": True,
                    "issue": "Needs live HTTP 200 verification" if status == "valid_format" else "Malformed URL"
                })
            except Exception as e:
                results.append({"url": url, "status": "error", "issue": str(e)})
                
        return results

    def get_freshness_report(self, content: str, topic: str = "", url: str = "") -> Dict[str, Any]:
        """Generates a comprehensive summary report of content freshness."""
        return {
            "freshness_score": self.calculate_freshness_score(content),
            "age_analysis": self.analyze_content_age(content),
            "signals": self.check_freshness_signals(content),
            "outdated_content": {
                "count": len(self.identify_outdated_content(content)),
                "stale_statistics_count": len(self.detect_stale_statistics(content))
            },
            "link_health": {
                "external_links_found": len(self.detect_broken_links(content)),
                "status": "requires_verification"
            },
            "suggestions": self.suggest_updates(content, topic),
            "refresh_schedule": self.set_refresh_schedule(content),
            "decay_tracking": self.track_content_decay(url) if url else None,
            "analyzed_at": self.current_date.isoformat()
        }
