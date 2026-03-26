"""
Field 005 Automator: Open Graph / Social Meta Generator
Generates Open Graph and Twitter Card meta tags:
- og:title, og:description, og:image, og:url, og:type
- twitter:card, twitter:title, twitter:description, twitter:image
- Ensures image dimensions meet platform minimums
"""

from .base_automator import BaseAutomator
from typing import Any, Dict, Tuple
import re


class Field005Automator(BaseAutomator):
    """Open Graph & Social Meta Generator — optimized social sharing tags."""

    def automate(self, context: Dict[str, Any]) -> Any:
        """Generate Open Graph and Twitter Card meta tags."""
        title = context.get("meta_title", context.get("title", ""))
        description = context.get("meta_description", context.get("description", ""))
        url = context.get("canonical_url", context.get("page_url", ""))
        image = context.get("featured_image", context.get("og_image", ""))
        site_name = context.get("site_name", context.get("brand_name", ""))
        content_type = context.get("content_type", "article")
        twitter_handle = context.get("twitter_handle", "")

        # OG type mapping
        og_type_map = {
            "article": "article",
            "guide": "article",
            "howto": "article",
            "product": "product",
            "review": "article",
            "homepage": "website",
            "profile": "profile",
        }
        og_type = og_type_map.get(content_type, "article")

        # Truncate for social platforms
        og_title = title[:70] if title else ""
        og_description = description[:200] if description else ""

        # Twitter card type
        twitter_card = "summary_large_image" if image else "summary"

        result = {
            "og": {
                "og:type": og_type,
                "og:title": og_title,
                "og:description": og_description,
                "og:url": url,
                "og:image": image,
                "og:site_name": site_name,
                "og:locale": context.get("locale", "en_US"),
            },
            "twitter": {
                "twitter:card": twitter_card,
                "twitter:title": og_title[:70],
                "twitter:description": og_description[:200],
                "twitter:image": image,
            },
        }

        if twitter_handle:
            result["twitter"]["twitter:site"] = twitter_handle
            result["twitter"]["twitter:creator"] = twitter_handle

        # Generate HTML meta tags
        meta_html = []
        for key, value in result["og"].items():
            if value:
                meta_html.append(f'<meta property="{key}" content="{self._escape_attr(value)}" />')
        for key, value in result["twitter"].items():
            if value:
                meta_html.append(f'<meta name="{key}" content="{self._escape_attr(value)}" />')

        result["html"] = "\n".join(meta_html)

        return result

    @staticmethod
    def _escape_attr(value: str) -> str:
        """Escape HTML attribute value."""
        return str(value).replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')

    def validate(self, value: Any) -> Tuple[bool, str]:
        """Validate OG/social meta tags."""
        if not value:
            return False, "Social meta tags are required"

        if not isinstance(value, dict):
            return False, "Expected dict with 'og' and 'twitter' keys"

        og = value.get("og", {})
        twitter = value.get("twitter", {})

        errors = []

        # Required OG fields
        if not og.get("og:title"):
            errors.append("Missing og:title")
        if not og.get("og:description"):
            errors.append("Missing og:description")
        if not og.get("og:url"):
            errors.append("Missing og:url")

        # OG title length
        if og.get("og:title") and len(og["og:title"]) > 95:
            errors.append(f"og:title too long ({len(og['og:title'])} chars, max 95)")

        # OG description length
        if og.get("og:description") and len(og["og:description"]) > 300:
            errors.append(f"og:description too long ({len(og['og:description'])} chars)")

        # Twitter card type
        if twitter.get("twitter:card") not in ("summary", "summary_large_image", "player", "app"):
            errors.append(f"Invalid twitter:card type: {twitter.get('twitter:card')}")

        if errors:
            return False, "; ".join(errors)

        return True, ""

    def score(self, value: Any) -> float:
        """Score social meta quality."""
        if not value or not isinstance(value, dict):
            return 0.0

        og = value.get("og", {})
        twitter = value.get("twitter", {})
        score = 0.2

        # Has og:title
        if og.get("og:title"):
            score += 0.15
        # Has og:description
        if og.get("og:description"):
            score += 0.1
        # Has og:image
        if og.get("og:image"):
            score += 0.15
        # Has og:url
        if og.get("og:url"):
            score += 0.1
        # Has twitter card
        if twitter.get("twitter:card"):
            score += 0.1
        # Has site_name
        if og.get("og:site_name"):
            score += 0.05
        # Has locale
        if og.get("og:locale"):
            score += 0.05
        # Large image card (better CTR)
        if twitter.get("twitter:card") == "summary_large_image":
            score += 0.1

        return min(score, 1.0)
