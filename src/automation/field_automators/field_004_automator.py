"""
Field 004 Automator: Canonical URL Generator
Sets the correct canonical URL to prevent duplicate content:
- Normalizes protocol (https preferred)
- Removes trailing slashes
- Strips URL parameters (tracking, session)
- Handles www/non-www consistency
- Validates URL format
"""

from .base_automator import BaseAutomator
from typing import Any, Dict, Tuple
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
import re

# URL parameters to strip (tracking/session params)
STRIP_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "dclid", "msclkid", "mc_eid",
    "ref", "referrer", "source", "sessionid", "session_id",
    "sid", "_ga", "_gl", "hsCtaTracking",
}


class Field004Automator(BaseAutomator):
    """Canonical URL Generator — prevents duplicate content issues."""

    def automate(self, context: Dict[str, Any]) -> Any:
        """Generate the canonical URL for a page."""
        url = context.get("page_url", context.get("target_url", context.get("url", "")))
        prefer_www = context.get("prefer_www", False)
        force_https = context.get("force_https", True)

        if not url:
            return ""

        # Parse URL
        parsed = urlparse(url)

        # Force HTTPS
        scheme = "https" if force_https else (parsed.scheme or "https")

        # Normalize hostname
        hostname = parsed.hostname or parsed.netloc or ""
        hostname = hostname.lower()

        # www consistency
        if prefer_www and not hostname.startswith("www."):
            hostname = f"www.{hostname}"
        elif not prefer_www and hostname.startswith("www."):
            hostname = hostname[4:]

        # Add port back if non-standard
        port = parsed.port
        netloc = hostname
        if port and port not in (80, 443):
            netloc = f"{hostname}:{port}"

        # Normalize path
        path = parsed.path or "/"
        # Remove duplicate slashes
        path = re.sub(r'/+', '/', path)
        # Remove trailing slash (except root)
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        # Lowercase path
        path = path.lower()

        # Strip tracking parameters
        if parsed.query:
            params = parse_qs(parsed.query, keep_blank_values=True)
            clean_params = {
                k: v for k, v in params.items()
                if k.lower() not in STRIP_PARAMS
            }
            query = urlencode(clean_params, doseq=True) if clean_params else ""
        else:
            query = ""

        # Remove fragment (anchors don't change canonical)
        fragment = ""

        canonical = urlunparse((scheme, netloc, path, "", query, fragment))
        return canonical

    def validate(self, value: Any) -> Tuple[bool, str]:
        """Validate canonical URL format."""
        if not value:
            return False, "Canonical URL is required"

        url = str(value)

        # Must be a valid URL
        parsed = urlparse(url)
        if not parsed.scheme:
            return False, "URL missing scheme (https://)"
        if parsed.scheme not in ("http", "https"):
            return False, f"Invalid scheme '{parsed.scheme}' (must be http/https)"
        if not parsed.netloc:
            return False, "URL missing domain"
        if parsed.fragment:
            return False, "Canonical URL should not include fragment (#)"

        # Check for tracking params that should be stripped
        if parsed.query:
            params = parse_qs(parsed.query)
            leftover = [k for k in params if k.lower() in STRIP_PARAMS]
            if leftover:
                return False, f"Canonical contains tracking params: {leftover}"

        return True, ""

    def score(self, value: Any) -> float:
        """Score canonical URL quality."""
        if not value:
            return 0.0

        url = str(value)
        parsed = urlparse(url)
        score = 0.3

        # HTTPS
        if parsed.scheme == "https":
            score += 0.2

        # Clean path (no duplicates, lowercase)
        if "//" not in parsed.path[1:]:
            score += 0.1
        if parsed.path == parsed.path.lower():
            score += 0.1

        # No tracking params
        if not parsed.query:
            score += 0.15
        else:
            params = parse_qs(parsed.query)
            if not any(k.lower() in STRIP_PARAMS for k in params):
                score += 0.1

        # No fragment
        if not parsed.fragment:
            score += 0.1

        # Reasonable path depth (< 5 segments)
        depth = len([s for s in parsed.path.split("/") if s])
        if depth <= 3:
            score += 0.05

        return min(score, 1.0)
