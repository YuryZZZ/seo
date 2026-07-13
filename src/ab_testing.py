import math
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SEOTestCase:
    """Represents an active or completed SEO A/B test case."""
    def __init__(
        self,
        test_id: str,
        url_pattern: str,
        variant_a_title: str,
        variant_b_title: str,
        variant_a_meta: str,
        variant_b_meta: str,
        traffic_split: float = 0.5
    ):
        self.test_id = test_id
        self.url_pattern = url_pattern
        self.variant_a_title = variant_a_title
        self.variant_b_title = variant_b_title
        self.variant_a_meta = variant_a_meta
        self.variant_b_meta = variant_b_meta
        self.traffic_split = traffic_split
        self.status = "active"
        
        # Metrics
        self.impressions_a = 0
        self.clicks_a = 0
        self.impressions_b = 0
        self.clicks_b = 0
        
        self.start_date = datetime.utcnow().isoformat()
        self.end_date: Optional[str] = None

    def update_metrics(self, impressions_a: int, clicks_a: int, impressions_b: int, clicks_b: int) -> None:
        self.impressions_a = impressions_a
        self.clicks_a = clicks_a
        self.impressions_b = impressions_b
        self.clicks_b = clicks_b

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "url_pattern": self.url_pattern,
            "variant_a_title": self.variant_a_title,
            "variant_b_title": self.variant_b_title,
            "variant_a_meta": self.variant_a_meta,
            "variant_b_meta": self.variant_b_meta,
            "traffic_split": self.traffic_split,
            "status": self.status,
            "impressions_a": self.impressions_a,
            "clicks_a": self.clicks_a,
            "impressions_b": self.impressions_b,
            "clicks_b": self.clicks_b,
            "start_date": self.start_date,
            "end_date": self.end_date
        }


class CloudflareWorkerGenerator:
    """Generates Cloudflare Worker scripts to rewrite SEO elements at the edge."""
    
    @staticmethod
    def generate(test_id: str, url_pattern: str, title_a: str, title_b: str, meta_a: str, meta_b: str, traffic_split: float = 0.5) -> str:
        """
        Generates JavaScript code for a Cloudflare Worker performing HTML rewriting.
        """
        worker_code = f"""// Cloudflare Worker for SEO A/B Test: {test_id}
const TRAFFIC_SPLIT = {traffic_split};
const URL_PATTERN = new RegExp('{url_pattern}');

addEventListener('fetch', event => {{
  event.respondWith(handleRequest(event.request));
}});

async function handleRequest(request) {{
  const url = new URL(request.url);
  if (!URL_PATTERN.test(url.pathname)) {{
    return fetch(request);
  }}

  // Route traffic using a deterministic hash of client IP
  const clientIP = request.headers.get('cf-connecting-ip') || '127.0.0.1';
  const bucket = hashString(clientIP) % 100 / 100;
  const useVariantB = bucket < TRAFFIC_SPLIT;

  const response = await fetch(request);
  const rewriter = new HTMLRewriter();

  if (useVariantB) {{
    rewriter.on('title', {{
      element(element) {{
        element.text('{title_b}');
      }}
    }});
    rewriter.on('meta[name="description"]', {{
      element(element) {{
        element.setAttribute('content', '{meta_b}');
      }}
    }});
  }} else {{
    rewriter.on('title', {{
      element(element) {{
        element.text('{title_a}');
      }}
    }});
    rewriter.on('meta[name="description"]', {{
      element(element) {{
        element.setAttribute('content', '{meta_a}');
      }}
    }});
  }}

  const newResponse = rewriter.transform(response);
  newResponse.headers.set('x-seo-ab-test-id', '{test_id}');
  newResponse.headers.set('x-seo-ab-variant', useVariantB ? 'B' : 'A');
  return newResponse;
}}

function hashString(str) {{
  let hash = 0;
  for (let i = 0; i < str.length; i++) {{
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }}
  return Math.abs(hash);
}}
"""
        return worker_code


class StatsCalculator:
    """Performs statistical significance checks on CTR results."""
    
    @staticmethod
    def _erf(x: float) -> float:
        """Approximates the error function erf(x)."""
        # Constants
        a1 =  0.254829592
        a2 = -0.284496736
        a3 =  1.421413741
        a4 = -1.453152027
        a5 =  1.061405429
        p  =  0.3275911

        sign = 1 if x >= 0 else -1
        x = abs(x)

        # A&S formula 7.1.26
        t = 1.0 / (1.0 + p * x)
        y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)
        return sign * y

    @classmethod
    def _normal_cdf(cls, z: float) -> float:
        """Calculates cumulative normal distribution Φ(z)."""
        return 0.5 * (1.0 + cls._erf(z / math.sqrt(2.0)))

    @classmethod
    def z_test_proportions(cls, n_a: int, clicks_a: int, n_b: int, clicks_b: int) -> Dict[str, Any]:
        """
        Computes the Z-test for two independent proportions (Variant A vs Variant B CTR).
        """
        if n_a <= 0 or n_b <= 0:
            return {
                "ctr_a": 0.0,
                "ctr_b": 0.0,
                "z_score": 0.0,
                "p_value": 1.0,
                "is_significant": False,
                "relative_difference": 0.0
            }

        p_a = clicks_a / n_a
        p_b = clicks_b / n_b

        # Relative change
        rel_diff = (p_b - p_a) / p_a if p_a > 0 else 0.0

        # Pooled proportion
        total_clicks = clicks_a + clicks_b
        total_impressions = n_a + n_b
        
        if total_clicks == 0:
            return {
                "ctr_a": round(p_a, 4),
                "ctr_b": round(p_b, 4),
                "z_score": 0.0,
                "p_value": 1.0,
                "is_significant": False,
                "relative_difference": round(rel_diff, 4)
            }

        p_pooled = total_clicks / total_impressions
        
        # Standard error
        se = math.sqrt(p_pooled * (1 - p_pooled) * (1 / n_a + 1 / n_b))
        
        if se == 0:
            z_score = 0.0
        else:
            z_score = (p_b - p_a) / se

        # Two-tailed p-value
        p_value = 2.0 * (1.0 - cls._normal_cdf(abs(z_score)))

        return {
            "ctr_a": round(p_a, 4),
            "ctr_b": round(p_b, 4),
            "z_score": round(z_score, 4),
            "p_value": round(p_value, 4),
            "is_significant": p_value < 0.05,
            "relative_difference": round(rel_diff, 4)
        }


class RollbackMechanism:
    """Manages evaluation and automatic rollback logic for underperforming tests."""
    
    def __init__(self, rollback_threshold: float = -0.15):
        """
        Args:
            rollback_threshold: Relative drop in CTR (e.g. -0.15 represents -15%).
        """
        self.rollback_threshold = rollback_threshold

    def evaluate_test(self, test: SEOTestCase) -> Dict[str, Any]:
        """
        Evaluates the test case and changes status to 'rolled_back' if threshold is violated
        with statistical significance.
        """
        stats = StatsCalculator.z_test_proportions(
            test.impressions_a, test.clicks_a,
            test.impressions_b, test.clicks_b
        )
        
        rollback_triggered = False
        message = "Test continues to run normally."
        
        if stats["is_significant"] and stats["relative_difference"] <= self.rollback_threshold:
            test.status = "rolled_back"
            test.end_date = datetime.utcnow().isoformat()
            rollback_triggered = True
            message = (
                f"ROLLBACK TRIGGERED: Variant B had a statistically significant "
                f"relative CTR drop of {round(stats['relative_difference'] * 100, 2)}% "
                f"which violates the limit of {round(self.rollback_threshold * 100, 2)}%."
            )
            
        return {
            "test_id": test.test_id,
            "status": test.status,
            "rollback_triggered": rollback_triggered,
            "message": message,
            "statistics": stats
        }
