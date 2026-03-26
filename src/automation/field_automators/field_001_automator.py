"""
Field 001 Automator: Meta Title Generator
Generates SEO-optimized page titles following best practices:
- 50-60 chars (55 optimal for Google SERP display)
- Focus keyword at front
- Brand at end (if provided)
- Power words for CTR
"""

from .base_automator import BaseAutomator
from typing import Any, Dict, Tuple
import re

POWER_WORDS = [
    "Ultimate", "Complete", "Proven", "Essential", "Expert",
    "Professional", "Definitive", "Comprehensive", "Advanced", "Top"
]


class Field001Automator(BaseAutomator):
    """Meta Title Generator — SEO-optimized <title> tag content."""

    def automate(self, context: Dict[str, Any]) -> Any:
        """Generate an SEO-optimized meta title."""
        keyword = context.get("focus_keyword", context.get("keyword", ""))
        brand = context.get("brand_name", "")
        content_type = context.get("content_type", "guide")
        year = context.get("year", "2025")

        if not keyword:
            return ""

        # Build title variants and pick the best fitting one
        keyword_title = keyword.title()

        templates = [
            f"{keyword_title}: The {POWER_WORDS[0]} Guide ({year})",
            f"{keyword_title} - {POWER_WORDS[3]} Tips & Best Practices",
            f"{POWER_WORDS[6]} {keyword_title} Guide for {year}",
            f"How to Master {keyword_title} in {year}",
            f"{keyword_title}: {POWER_WORDS[2]} Strategies That Work",
        ]

        # Pick the template that fits 50-60 chars best
        best_title = templates[0]
        best_diff = abs(len(templates[0]) - 55)

        for t in templates:
            diff = abs(len(t) - 55)
            if diff < best_diff:
                best_title = t
                best_diff = diff

        # Append brand if room allows
        if brand and len(best_title) + len(brand) + 3 <= 60:
            best_title = f"{best_title} | {brand}"

        # Truncate if still too long
        if len(best_title) > 60:
            best_title = best_title[:57] + "..."

        return best_title

    def validate(self, value: Any) -> Tuple[bool, str]:
        """Validate meta title meets SEO requirements."""
        if not value:
            return False, "Meta title is required"

        title = str(value)

        if len(title) < 20:
            return False, f"Title too short ({len(title)} chars, need 20+)"

        if len(title) > 65:
            return False, f"Title too long ({len(title)} chars, max 65)"

        if title.lower() == title:
            return False, "Title should use title case or sentence case"

        return True, ""

    def score(self, value: Any) -> float:
        """Score meta title quality (0.0 to 1.0)."""
        if not value:
            return 0.0

        title = str(value)
        score = 0.3  # Base score for having any title

        # Optimal length (50-60 chars)
        if 50 <= len(title) <= 60:
            score += 0.3
        elif 40 <= len(title) <= 65:
            score += 0.15

        # Contains a power word
        title_lower = title.lower()
        if any(pw.lower() in title_lower for pw in POWER_WORDS):
            score += 0.1

        # Contains a year (freshness signal)
        if re.search(r'20[2-3]\d', title):
            score += 0.1

        # Starts with keyword (not "How to" or other prefix)
        if not title.startswith(("How", "The", "A ", "An ")):
            score += 0.1

        # Contains separator (| or - or :)
        if any(sep in title for sep in [" | ", " - ", ": "]):
            score += 0.1

        return min(score, 1.0)
