"""
Field 003 Automator: URL Slug Generator
Creates SEO-friendly URL slugs:
- 3-5 words (50-75 chars max)
- Contains focus keyword
- No stop words
- Lowercase, hyphenated
- No special characters
"""

from .base_automator import BaseAutomator
from typing import Any, Dict, Tuple
import re

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can", "shall",
    "this", "that", "these", "those", "it", "its", "your", "our",
    "my", "their", "his", "her", "not", "no", "so", "if", "then",
    "than", "too", "very", "just",
}


class Field003Automator(BaseAutomator):
    """URL Slug Generator — SEO-friendly URL path segments."""

    def automate(self, context: Dict[str, Any]) -> Any:
        """Generate an SEO-optimized URL slug."""
        keyword = context.get("focus_keyword", context.get("keyword", ""))
        title = context.get("title", context.get("meta_title", ""))

        source = keyword or title
        if not source:
            return ""

        # Normalize: lowercase, strip special chars
        slug = source.lower().strip()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'\s+', ' ', slug).strip()

        # Remove stop words (but keep keyword intact)
        words = slug.split()
        keyword_words = set(keyword.lower().split()) if keyword else set()

        filtered = []
        for w in words:
            if w in keyword_words or w not in STOP_WORDS:
                filtered.append(w)

        # Limit to 5 words
        if len(filtered) > 5:
            # Prioritize keyword words
            kw_words = [w for w in filtered if w in keyword_words]
            other_words = [w for w in filtered if w not in keyword_words]
            remaining_slots = 5 - len(kw_words)
            filtered = kw_words + other_words[:max(0, remaining_slots)]

        slug = "-".join(filtered)

        # Ensure slug isn't too long
        if len(slug) > 75:
            slug = slug[:75].rsplit("-", 1)[0]

        return slug

    def validate(self, value: Any) -> Tuple[bool, str]:
        """Validate URL slug meets SEO requirements."""
        if not value:
            return False, "URL slug is required"

        slug = str(value)

        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', slug):
            return False, "Slug must be lowercase alphanumeric with hyphens, no leading/trailing hyphens"

        if '--' in slug:
            return False, "Slug contains consecutive hyphens"

        if len(slug) > 75:
            return False, f"Slug too long ({len(slug)} chars, max 75)"

        if len(slug) < 3:
            return False, f"Slug too short ({len(slug)} chars, min 3)"

        word_count = slug.count("-") + 1
        if word_count > 7:
            return False, f"Slug has too many segments ({word_count}, max 7)"

        return True, ""

    def score(self, value: Any) -> float:
        """Score URL slug quality."""
        if not value:
            return 0.0

        slug = str(value)
        score = 0.3

        # Optimal length (15-50 chars)
        if 15 <= len(slug) <= 50:
            score += 0.25
        elif 10 <= len(slug) <= 75:
            score += 0.1

        # Optimal word count (3-5 words)
        word_count = slug.count("-") + 1
        if 3 <= word_count <= 5:
            score += 0.2
        elif 2 <= word_count <= 7:
            score += 0.1

        # No consecutive hyphens
        if '--' not in slug:
            score += 0.1

        # No numbers (cleaner URLs)
        if not re.search(r'\d', slug):
            score += 0.05

        # Doesn't start with a year
        if not re.match(r'^20\d\d', slug):
            score += 0.1

        return min(score, 1.0)
