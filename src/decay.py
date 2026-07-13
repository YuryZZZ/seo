import math
import difflib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ContentDecayAnalyzer:
    """
    Analyzes historical search performance metrics to identify decay trends
    and calculate freshness/traffic loss scores.
    """
    def __init__(self, time_decay_half_life_days: float = 180.0):
        # lambda = ln(2) / half_life
        self.decay_lambda = math.log(2.0) / time_decay_half_life_days

    def calculate_time_decay(self, last_modified_iso: str) -> float:
        """
        Calculates freshness decay score using an exponential decay model:
        Decay = 1.0 - exp(-lambda * days_elapsed)
        """
        try:
            last_mod = datetime.fromisoformat(last_modified_iso)
        except Exception:
            # Fallback to current date minus 1 year if invalid format
            last_mod = datetime.utcnow() - timedelta(days=365)
            
        elapsed_days = (datetime.utcnow() - last_mod).days
        elapsed_days = max(0, elapsed_days)
        
        # Exponential decay factor: 0.0 at day 0, approaches 1.0 as time passes
        decay_factor = 1.0 - math.exp(-self.decay_lambda * elapsed_days)
        return round(decay_factor, 4)

    def calculate_traffic_drop(self, current_30_clicks: int, baseline_90_clicks: int) -> float:
        """
        Calculates the percentage traffic drop relative to the baseline.
        The baseline is adjusted to 30-day equivalents.
        """
        if baseline_90_clicks <= 0:
            return 0.0
            
        # Adjust 90-day baseline to a 30-day equivalent
        baseline_30_equiv = baseline_90_clicks / 3.0
        
        if current_30_clicks >= baseline_30_equiv:
            return 0.0
            
        drop = (baseline_30_equiv - current_30_clicks) / baseline_30_equiv
        return round(drop, 4)

    def calculate_decay_score(self, last_modified_iso: str,
                              current_30_clicks: int,
                              baseline_90_clicks: int,
                              weight_traffic: float = 0.7,
                              weight_time: float = 0.3) -> float:
        """
        Computes a combined normalized decay score between 0.0 and 1.0.
        """
        time_decay = self.calculate_time_decay(last_modified_iso)
        traffic_drop = self.calculate_traffic_drop(current_30_clicks, baseline_90_clicks)
        
        score = (traffic_drop * weight_traffic) + (time_decay * weight_time)
        return round(min(1.0, max(0.0, score)), 4)


class ContentRefreshStrategy:
    """
    Formulates strategies and prompts for refreshing decaying pages.
    """
    def __init__(self, llm_client=None):
        self.llm = llm_client

    def generate_refresh_prompt(self, current_content: str,
                                 focus_keyword: str,
                                 missing_lsi: List[str],
                                 target_year: int = 2026) -> str:
        """
        Builds an optimized LLM system prompt requesting a refresh of the page content.
        """
        lsi_str = ", ".join(missing_lsi) if missing_lsi else "None"
        prompt = f"""You are an expert SEO Copywriter. Review and refresh the content below.

OBJECTIVES:
1. Update any obsolete statistics, claims, or old dates/years (e.g. replace "2024" or "2025" references with "{target_year}").
2. Naturally integrate these missing LSI entities/keywords to improve semantic coverage: {lsi_str}.
3. Maintain the exact same voice, tone, and formatting (keep markdown headings and HTML tags intact).
4. Do NOT drop the overall word count. Keep existing high-quality paragraphs intact.

FOCUS KEYWORD: {focus_keyword}

CURRENT CONTENT:
\"\"\"
{current_content}
\"\"\"

OUTPUT: Return ONLY the fully updated and refreshed content, with no introductory or concluding sentences.
"""
        return prompt

    def refresh_page_content(self, current_content: str,
                             focus_keyword: str,
                             missing_lsi: List[str],
                             target_year: int = 2026) -> str:
        """
        Invokes the LLM client to refresh the page content.
        """
        if not self.llm:
            # Simple offline string replacement fallback for testing
            refreshed = current_content
            # Replace older years
            for old_year in ["2024", "2025"]:
                refreshed = refreshed.replace(old_year, str(target_year))
            # Inject LSI
            if missing_lsi:
                refreshed += f"\n\nAdditional topics to consider: {', '.join(missing_lsi)}."
            return refreshed
            
        prompt = self.generate_refresh_prompt(current_content, focus_keyword, missing_lsi, target_year)
        try:
            refreshed = self.llm.generate(prompt, temperature=0.5, max_tokens=2500)
            return refreshed.strip()
        except Exception as e:
            logger.error(f"Failed to refresh content via LLM: {e}")
            return current_content


class DiffComparisonTool:
    """
    Generates side-by-side or line-by-line differences of old vs new content.
    """
    @staticmethod
    def generate_html_diff(old_content: str, new_content: str) -> str:
        """
        Returns a clean HTML representation of line-by-line diff changes.
        """
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        
        diff = difflib.HtmlDiff()
        return diff.make_file(old_lines, new_lines, context=True, numlines=3)
