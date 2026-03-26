"""
Field 002 Automator: Meta Description Generator
Generates compelling meta descriptions for SERP display:
- 150-160 chars (155 optimal)
- Contains focus keyword naturally
- Includes a call to action
- Uses active voice
"""

from .base_automator import BaseAutomator
from typing import Any, Dict, Tuple
import re

CTA_PHRASES = [
    "Learn more", "Discover", "Find out how", "Get started",
    "Read our guide", "See examples", "Compare options",
]


class Field002Automator(BaseAutomator):
    """Meta Description Generator — compelling SERP snippet text."""

    def automate(self, context: Dict[str, Any]) -> Any:
        """Generate an SEO-optimized meta description."""
        keyword = context.get("focus_keyword", context.get("keyword", ""))
        content = context.get("content", "")
        bluf = context.get("bluf", "")
        content_type = context.get("content_type", "guide")

        if not keyword:
            return ""

        # Try to use BLUF as desc basis if available
        if bluf and len(bluf) >= 50:
            desc = bluf.strip()
            if len(desc) > 160:
                desc = desc[:157] + "..."
            # Ensure keyword is present
            if keyword.lower() not in desc.lower():
                desc = f"{keyword.title()}: {desc}"
                if len(desc) > 160:
                    desc = desc[:157] + "..."
            return desc

        # Generate from scratch based on content type
        templates = {
            "guide": f"Comprehensive guide to {keyword}. Learn expert strategies, best practices, and proven tips to improve your results. {CTA_PHRASES[0]}.",
            "howto": f"Step-by-step guide on {keyword}. Follow our proven process to achieve measurable results. {CTA_PHRASES[3]} today.",
            "review": f"In-depth review of {keyword}. {CTA_PHRASES[6]} and find the best option for your needs.",
            "list": f"Top {keyword} options reviewed and ranked. {CTA_PHRASES[1]} which solutions deliver the best results.",
        }

        desc = templates.get(content_type, templates["guide"])

        # Fit to 155 chars
        if len(desc) > 160:
            desc = desc[:157] + "..."
        elif len(desc) < 120:
            desc = desc.rstrip(".") + f". {CTA_PHRASES[4]}."

        return desc

    def validate(self, value: Any) -> Tuple[bool, str]:
        """Validate meta description meets SEO requirements."""
        if not value:
            return False, "Meta description is required"

        desc = str(value)

        if len(desc) < 50:
            return False, f"Description too short ({len(desc)} chars, need 50+)"

        if len(desc) > 165:
            return False, f"Description too long ({len(desc)} chars, max 165)"

        # Should not contain double quotes (breaks HTML attr)
        if '"' in desc:
            return False, "Description contains double quotes (will break HTML)"

        return True, ""

    def score(self, value: Any) -> float:
        """Score meta description quality."""
        if not value:
            return 0.0

        desc = str(value)
        score = 0.3

        # Optimal length (150-160)
        if 150 <= len(desc) <= 160:
            score += 0.25
        elif 120 <= len(desc) <= 165:
            score += 0.1

        # Contains CTA
        desc_lower = desc.lower()
        if any(cta.lower() in desc_lower for cta in CTA_PHRASES):
            score += 0.15

        # Ends with period or CTA
        if desc.rstrip().endswith((".", "!", "today.", "more.")):
            score += 0.1

        # Active voice indicators
        if any(w in desc_lower for w in ["learn", "discover", "find", "get", "improve", "compare"]):
            score += 0.1

        # No keyword stuffing (same word >3 times)
        words = desc_lower.split()
        if words:
            from collections import Counter
            freq = Counter(w for w in words if len(w) > 4)
            if all(c <= 3 for c in freq.values()):
                score += 0.1

        return min(score, 1.0)
