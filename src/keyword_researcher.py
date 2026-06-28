"""Keyword research + SEO framework builder for automation pipelines."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

import yaml

try:
    from .content_utils import slugify
except ImportError:  # pragma: no cover
    from content_utils import slugify


@dataclass
class KeywordResult:
    keyword: str
    volume: int
    competition: float
    cpc: float
    trend: str
    related: List[str] = field(default_factory=list)


class KeywordResearcher:
    """Builds keyword maps and full SEO site/app frameworks."""

    DEFAULT_SERVICES = [
        "taskbus_postgres",
        "google_search_console",
        "google_custom_search",
        "brave_search",
        "tavily_search",
        "perplexity_search",
        "glm_search",
        "youtube_data_api",
    ]

    INTENTS = ["informational", "commercial", "transactional", "navigational"]

    INTENT_MODIFIERS = {
        "informational": ["guide", "explained", "best practices", "framework", "checklist", "template"],
        "commercial": ["pricing", "cost", "comparison", "vendors", "tools", "platforms"],
        "transactional": ["services", "consulting", "implementation", "audit", "rfp", "proposal"],
        "navigational": ["docs", "api", "workflow", "integration", "setup", "examples"],
    }

    QUESTION_PREFIXES = ["how to", "what is", "why", "when should", "which"]

    REPO_FILE_SUFFIXES = {
        ".py",
        ".md",
        ".yaml",
        ".yml",
        ".json",
        ".txt",
        ".rst",
        ".toml",
        ".ini",
        ".csv",
    }

    SKIP_DIR_NAMES = {
        ".git",
        ".ai",
        ".benchmarks",
        ".mcp",
        ".sessions",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "node_modules",
        "docs",
        "output",
        "implementations",
        "portable",
        "research_100x",
    }

    STOPWORDS = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "this",
        "that",
        "into",
        "your",
        "about",
        "json",
        "true",
        "false",
        "null",
        "none",
        "class",
        "def",
        "import",
        "return",
    }

    DOMAIN_ROOTS = {
        "cost",
        "contract",
        "vendor",
        "pricing",
        "procurement",
        "legal",
        "compliance",
        "audit",
        "risk",
        "service",
        "api",
        "agreement",
        "renewal",
        "termination",
        "negotiation",
        "implementation",
        "governance",
        "budget",
        "roi",
        "privacy",
        "security",
        "data",
        "clause",
        "liability",
        "indemnity",
        "jurisdiction",
        "dispute",
        "sla",
    }

    def __init__(self, enable_live: bool = True, repo_root: Optional[Path] = None, config: Optional[Dict[str, Any]] = None):
        self.enable_live = enable_live
        self.repo_root = repo_root or Path(__file__).resolve().parents[1]
        self.config = config or {}
        # Paid SEO scrapers are intentionally disabled in this project mode.
        self.google_api_key = self.config.get("google_api_key") or os.getenv("GOOGLE_API_KEY")
        self.google_search_engine_id = (
            self.config.get("google_search_engine_id")
            or self.config.get("google_cx")
            or os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        )
        self.gsc_api_key = self.config.get('gsc_api_key')
        self.cache: Dict[str, KeywordResult] = {}
        self._repository_scan_cache: Dict[int, Tuple[List[str], Dict[str, Any]]] = {}

    def research(self, seed_keyword: str) -> List[KeywordResult]:
        report = self.research_keywords(seed_keyword, limit=20)
        rows = report.get("top_opportunities", [])
        return [
            KeywordResult(
                keyword=row["keyword"],
                volume=row["search_volume"],
                competition=row["competition"],
                cpc=row["cpc"],
                trend=row["trend"],
                related=row.get("related", []),
            )
            for row in rows
        ]

    def research_keywords(self, seed_keyword: str, limit: int = 30) -> Dict[str, Any]:
        keyword_rows = self._build_keyword_rows(
            seed_keyword=seed_keyword,
            target_count=max(limit, 10),
            include_questions=True,
            include_contract_defaults=False,
        )

        # Enrich with real DuckDuckGo search data
        ddg_keywords = self._enrich_with_ddg(seed_keyword)
        existing_kws = {row["keyword"].lower() for row in keyword_rows}
        for kw in ddg_keywords:
            if kw.lower() not in existing_kws and len(keyword_rows) < limit + 20:
                existing_kws.add(kw.lower())
                keyword_rows.append(self._keyword_row(
                    keyword=kw,
                    intent=self._infer_intent(kw),
                    index=len(keyword_rows),
                ))

        # Enrich with real Google Custom Search data
        google_keywords = self._enrich_with_google_search(seed_keyword)
        for kw in google_keywords:
            if kw.lower() not in existing_kws and len(keyword_rows) < limit + 20:
                existing_kws.add(kw.lower())
                keyword_rows.append(self._keyword_row(
                    keyword=kw,
                    intent=self._infer_intent(kw),
                    index=len(keyword_rows),
                ))

        clustered: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for row in keyword_rows:
            clustered[row["intent"]].append(row)

        top = sorted(keyword_rows, key=lambda item: item["opportunity_score"], reverse=True)[: min(12, len(keyword_rows))]
        clusters = {
            intent: [item["keyword"] for item in rows[: max(3, min(10, limit // 2))]]
            for intent, rows in clustered.items()
        }

        return {
            "seed_keyword": seed_keyword,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_keywords": len(keyword_rows),
            "clusters": clusters,
            "top_opportunities": top,
            "ddg_enriched": len(ddg_keywords),
            "google_enriched": len(google_keywords),
        }

    def _enrich_with_ddg(self, seed_keyword: str) -> List[str]:
        """Discover real related keywords from DuckDuckGo search results."""
        try:
            try:
                from .integrations.duckduckgo_client import DuckDuckGoClient
            except ImportError:
                try:
                    from integrations.duckduckgo_client import DuckDuckGoClient
                except ImportError:
                    return []

            client = DuckDuckGoClient()
            results = client.search_sync(seed_keyword, max_results=10, region="uk-en")
            if not results:
                return []

            discovered = []
            seed_words = set(seed_keyword.lower().split())

            for r in results:
                title = r.get("title", "")
                body = r.get("body", "")
                # Extract meaningful phrases from titles
                if title:
                    # Clean title: remove site names after | or -
                    clean_title = re.split(r'\s*[|–—-]\s*', title)[0].strip()
                    if len(clean_title) > 10 and len(clean_title) < 80:
                        title_words = set(clean_title.lower().split())
                        if title_words & seed_words:  # Must share at least one word with seed
                            discovered.append(clean_title.lower())

                # Extract long-tail keywords from snippets
                if body:
                    # Find quoted or emphasized phrases
                    phrases = re.findall(r'([A-Z][a-z]+(?:\s+[a-z]+){1,4})', body)
                    for phrase in phrases:
                        phrase_lower = phrase.lower()
                        phrase_words = set(phrase_lower.split())
                        if phrase_words & seed_words and len(phrase_lower) > 10:
                            discovered.append(phrase_lower)

            # Also get suggestions
            suggestions = client.get_suggestions(seed_keyword, region="uk-en")
            for s in suggestions:
                clean = re.split(r'\s*[|–—-]\s*', s)[0].strip().lower()
                if clean and len(clean) > 8:
                    discovered.append(clean)

            # Deduplicate
            seen = set()
            unique = []
            for kw in discovered:
                kw_norm = kw.strip().lower()
                if kw_norm not in seen and kw_norm != seed_keyword.lower():
                    seen.add(kw_norm)
                    unique.append(kw_norm)

            return unique[:15]

        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"DuckDuckGo keyword enrichment failed: {e}")
            return []

    def _enrich_with_google_search(self, seed_keyword: str) -> List[str]:
        """Discover real related keywords from Google Custom Search results."""
        if not (self.google_api_key and self.google_search_engine_id):
            return []
        try:
            try:
                from src.apis.google_custom_search import GoogleCustomSearchAPI
            except ImportError:
                from apis.google_custom_search import GoogleCustomSearchAPI

            api = GoogleCustomSearchAPI(
                api_key=self.google_api_key,
                search_engine_id=self.google_search_engine_id,
            )
            response = api.search(seed_keyword, num=10)
            if response.get("status") != "ok":
                return []

            data = response.get("data", {})
            discovered = []
            seed_words = set(seed_keyword.lower().split())

            for item in data.get("items", []):
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                if title:
                    clean_title = re.split(r'\s*[|–—-]\s*', title)[0].strip()
                    if len(clean_title) > 10 and len(clean_title) < 80:
                        title_words = set(clean_title.lower().split())
                        if title_words & seed_words:
                            discovered.append(clean_title.lower())
                if snippet:
                    phrases = re.findall(r'\b[A-Za-z0-9\s-]{10,40}\b', snippet)
                    for p in phrases:
                        p_words = set(p.lower().split())
                        if p_words & seed_words:
                            discovered.append(p.strip().lower())

            # Deduplicate
            seen = set()
            unique = []
            for kw in discovered:
                kw_norm = kw.strip().lower()
                if kw_norm not in seen and kw_norm != seed_keyword.lower():
                    seen.add(kw_norm)
                    unique.append(kw_norm)
            return unique[:15]
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Google Custom Search keyword enrichment failed: {e}")
            return []

    def _infer_intent(self, keyword: str) -> str:
        """Infer search intent from keyword text."""
        kw = keyword.lower()
        if any(w in kw for w in ["cost", "price", "quote", "how much", "cheap", "affordable", "budget"]):
            return "commercial"
        if any(w in kw for w in ["buy", "hire", "book", "near me", "company", "services", "contractor"]):
            return "transactional"
        if any(w in kw for w in ["what", "how", "why", "guide", "tips", "ideas", "explained"]):
            return "informational"
        return "informational"

    def build_costs_contracts_framework(
        self,
        base_url: str = "https://example.com",
        max_spokes_per_cluster: int = 6,
        max_repository_terms: int = 1200,
        target_keyword_count: int = 1200,
        target_topic_count: int = 133,
    ) -> Dict[str, Any]:
        repository_terms, scan_inventory = self._scan_repository_terms(max_repository_terms=max_repository_terms)

        keyword_universe = self._build_keyword_rows(
            seed_keyword="costs and contracts",
            target_count=max(300, target_keyword_count),
            include_questions=True,
            repository_terms=repository_terms,
            include_contract_defaults=True,
        )

        services_catalog = self._load_services_catalog()
        coverage_matrix = self._build_coverage_matrix(services_catalog)

        site = self._build_site_structure(
            keyword_universe=keyword_universe,
            coverage_matrix=coverage_matrix,
            max_spokes_per_cluster=max_spokes_per_cluster,
        )

        topics = self._build_topics(
            target_topic_count=max(12, target_topic_count),
            keyword_universe=keyword_universe,
            spokes=site["spokes"],
            coverage_matrix=coverage_matrix,
        )

        keyword_framework = self._build_keyword_framework(keyword_universe)
        service_map = self._build_service_page_topic_keyword_map(
            coverage_matrix=coverage_matrix,
            topics=topics,
            spokes=site["spokes"],
        )
        website_tree = self._build_website_structure_tree(site=site, topics=topics, coverage_matrix=coverage_matrix)

        dossier = {
            "topics": topics,
            "keyword_framework": keyword_framework,
            "service_page_topic_keyword_map": service_map,
            "site_structure_summary": {
                "cms": "framework-native (no wordpress dependency)",
                "base_url": base_url,
                "topic_count": len(topics),
                "keyword_count": len(keyword_universe),
                "service_count": len(coverage_matrix),
            },
            "repository_scan_inventory": scan_inventory,
            "website_structure_tree": website_tree,
            "core_topics": [topic["topic_name"] for topic in topics[:30]],
            "repository_signal_topics": repository_terms[:120],
        }

        quality_gates = self._evaluate_quality(
            keyword_universe=keyword_universe,
            topics=topics,
            service_map=service_map,
            coverage_matrix=coverage_matrix,
        )

        return {
            "topic": "costs and contracts",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "live_provider_status": {
                "enabled": self.enable_live,
                "mode": "synthetic_with_live_hooks" if self.enable_live else "synthetic_only",
                "providers": {
                    "google_custom_search": bool(self.google_api_key and self.google_search_engine_id),
                    "google_search_console": bool(self.gsc_api_key),
                    "brave_search": bool(self.config.get("brave_api_key") or os.getenv("BRAVE_SEARCH_API_KEY")),
                    "tavily_search": bool(self.config.get("tavily_api_key") or os.getenv("TAVILY_API_KEY")),
                    "perplexity_search": bool(
                        self.config.get("perplexity_api_key") or os.getenv("PERPLEXITY_API_KEY")
                    ),
                    "glm_search": bool(self.config.get("glm_api_key") or os.getenv("GLM_API_KEY")),
                },
            },
            "keyword_universe": keyword_universe,
            "site_structure": site,
            "coverage_matrix": coverage_matrix,
            "research_dossier": dossier,
            "repository_scan_inventory": scan_inventory,
            "quality_gates": quality_gates,
        }

    def build_seo_template_framework(
        self,
        seed_topic: str,
        base_url: str = "https://example.com",
        target_keyword_count: int = 600,
        target_topic_count: int = 48,
        max_spokes_per_cluster: int = 6,
        max_repository_terms: int = 800,
    ) -> Dict[str, Any]:
        """Build a generic SEO template/app framework for any topic or vertical."""
        normalized_topic = self._normalize_keyword(seed_topic or "seo strategy")
        topic_slug = slugify(normalized_topic)
        root_slug = f"/resources/{topic_slug}/"

        repository_terms, scan_inventory = self._scan_repository_terms(max_repository_terms=max_repository_terms)
        keyword_universe = self._build_keyword_rows(
            seed_keyword=normalized_topic,
            target_count=max(200, target_keyword_count),
            include_questions=True,
            repository_terms=repository_terms,
            include_contract_defaults=False,
        )

        app_matrix = self._build_seo_app_matrix(root_slug=root_slug)
        site = self._build_seo_site_structure(
            root_slug=root_slug,
            topic=normalized_topic,
            keyword_universe=keyword_universe,
            app_matrix=app_matrix,
            max_spokes_per_cluster=max_spokes_per_cluster,
        )
        topics = self._build_seo_topics(
            root_slug=root_slug,
            topic=normalized_topic,
            target_topic_count=max(12, target_topic_count),
            keyword_universe=keyword_universe,
            spokes=site["spokes"],
            app_matrix=app_matrix,
        )
        keyword_framework = self._build_keyword_framework(keyword_universe)
        app_map = self._build_seo_app_topic_keyword_map(app_matrix=app_matrix, topics=topics, spokes=site["spokes"])
        website_tree = self._build_seo_website_structure_tree(root_slug=root_slug, site=site, topics=topics, app_matrix=app_matrix)
        template_library = self._build_seo_template_library(root_slug=root_slug, topic=normalized_topic)
        app_flows = self._build_seo_app_flows(root_slug=root_slug, topic=normalized_topic)

        dossier = {
            "topics": topics,
            "keyword_framework": keyword_framework,
            "app_page_topic_keyword_map": app_map,
            "site_structure_summary": {
                "cms": "framework-native",
                "base_url": base_url,
                "root_slug": root_slug,
                "topic_count": len(topics),
                "keyword_count": len(keyword_universe),
                "app_count": len(app_matrix),
            },
            "website_structure_tree": website_tree,
            "repository_scan_inventory": scan_inventory,
            "template_library": template_library,
            "app_flows": app_flows,
        }

        quality_gates = self._evaluate_quality(
            keyword_universe=keyword_universe,
            topics=topics,
            service_map=app_map,
            coverage_matrix=app_matrix,
        )

        return {
            "topic": normalized_topic,
            "framework_type": "generic_seo_templates_and_apps",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "live_provider_status": {
                "enabled": self.enable_live,
                "mode": "synthetic_with_live_hooks" if self.enable_live else "synthetic_only",
                "providers": {
                    "google_custom_search": bool(self.google_api_key and self.google_search_engine_id),
                    "google_search_console": bool(self.gsc_api_key),
                    "brave_search": bool(self.config.get("brave_api_key") or os.getenv("BRAVE_SEARCH_API_KEY")),
                    "tavily_search": bool(self.config.get("tavily_api_key") or os.getenv("TAVILY_API_KEY")),
                    "perplexity_search": bool(self.config.get("perplexity_api_key") or os.getenv("PERPLEXITY_API_KEY")),
                    "glm_search": bool(self.config.get("glm_api_key") or os.getenv("GLM_API_KEY")),
                },
            },
            "keyword_universe": keyword_universe,
            "site_structure": site,
            "coverage_matrix": app_matrix,
            "research_dossier": dossier,
            "repository_scan_inventory": scan_inventory,
            "quality_gates": quality_gates,
            "template_library": template_library,
            "app_flows": app_flows,
        }

    def _build_seo_app_matrix(self, root_slug: str) -> List[Dict[str, Any]]:
        apps = [
            "keyword_research_app",
            "content_brief_app",
            "serp_tracking_app",
            "entity_schema_app",
            "internal_linking_app",
            "local_seo_app",
            "technical_audit_app",
            "analytics_iteration_app",
        ]
        rows: List[Dict[str, Any]] = []
        for name in apps:
            app_slug = slugify(name.replace("_", " "))
            rows.append(
                {
                    "service_name": name,
                    "app_name": name,
                    "dedicated_page_slug": f"{root_slug}apps/{app_slug}/",
                    "dedicated_sections": [
                        "overview",
                        "inputs",
                        "automation_flow",
                        "outputs",
                        "kpis",
                        "rollout_steps",
                    ],
                }
            )
        return rows

    def _build_seo_site_structure(
        self,
        root_slug: str,
        topic: str,
        keyword_universe: List[Dict[str, Any]],
        app_matrix: List[Dict[str, Any]],
        max_spokes_per_cluster: int,
    ) -> Dict[str, Any]:
        pillar = {
            "title": f"{topic.title()} SEO Hub",
            "slug": root_slug,
            "primary_keyword": topic,
            "target_word_count": 2600,
            "template": "pillar",
            "intent": "informational",
            "cluster": "core",
        }

        keywords_by_intent: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for row in keyword_universe:
            keywords_by_intent[row["intent"]].append(row)

        spokes: List[Dict[str, Any]] = []
        spoke_limit = max(2, max_spokes_per_cluster)
        for intent in self.INTENTS:
            candidates = sorted(
                keywords_by_intent.get(intent, []),
                key=lambda item: item["opportunity_score"],
                reverse=True,
            )[:spoke_limit]
            for idx, item in enumerate(candidates):
                raw_slug = slugify(item["keyword"])
                spokes.append(
                    {
                        "slug": f"{root_slug}{raw_slug}/",
                        "title": item["keyword"].title(),
                        "primary_keyword": item["keyword"],
                        "intent": intent,
                        "template": self._template_for_intent(intent),
                        "cluster": f"{intent}-cluster",
                        "target_word_count": 1400 + (idx * 80),
                    }
                )

        while len(spokes) < 8:
            idx = len(spokes)
            kw = keyword_universe[idx % len(keyword_universe)]
            spokes.append(
                {
                    "slug": f"{root_slug}{slugify(kw['keyword'])}-{idx + 1}/",
                    "title": kw["keyword"].title(),
                    "primary_keyword": kw["keyword"],
                    "intent": kw["intent"],
                    "template": self._template_for_intent(kw["intent"]),
                    "cluster": f"{kw['intent']}-cluster",
                    "target_word_count": 1500,
                }
            )

        unique_spokes: List[Dict[str, Any]] = []
        seen_slugs = set()
        for row in spokes:
            if row["slug"] in seen_slugs:
                continue
            seen_slugs.add(row["slug"])
            unique_spokes.append(row)
        spokes = unique_spokes

        page_briefs: Dict[str, Dict[str, Any]] = {
            pillar["slug"]: self._build_generic_page_brief(
                slug=pillar["slug"],
                title=pillar["title"],
                primary_keyword=pillar["primary_keyword"],
                template="pillar",
                cluster="core",
                target_word_count=pillar["target_word_count"],
                topic=topic,
            )
        }

        for spoke in spokes:
            page_briefs[spoke["slug"]] = self._build_generic_page_brief(
                slug=spoke["slug"],
                title=spoke["title"],
                primary_keyword=spoke["primary_keyword"],
                template=spoke["template"],
                cluster=spoke["cluster"],
                target_word_count=spoke["target_word_count"],
                topic=topic,
            )

        app_page_briefs: Dict[str, Dict[str, Any]] = {}
        for row in app_matrix:
            service_label = row["service_name"].replace("_", " ").title()
            app_page_briefs[row["dedicated_page_slug"]] = self._build_generic_page_brief(
                slug=row["dedicated_page_slug"],
                title=f"{service_label} Workflow",
                primary_keyword=f"{topic} {service_label.lower()}",
                template="app_page",
                cluster="apps",
                target_word_count=1400,
                topic=topic,
                required_sections=row["dedicated_sections"],
            )

        internal_links = self._build_internal_links(pillar_slug=pillar["slug"], spokes=spokes)
        self._attach_links_to_briefs(page_briefs, internal_links)
        self._attach_links_to_briefs(app_page_briefs, internal_links)

        outlines = {
            slug: {"title": brief["title"], "h2_outline": brief["h2_outline"]}
            for slug, brief in {**page_briefs, **app_page_briefs}.items()
        }

        return {
            "pillar": pillar,
            "spokes": spokes,
            "internal_links": internal_links,
            "page_briefs": page_briefs,
            "coverage_page_briefs": app_page_briefs,
            "outlines": outlines,
        }

    def _build_generic_page_brief(
        self,
        slug: str,
        title: str,
        primary_keyword: str,
        template: str,
        cluster: str,
        target_word_count: int,
        topic: str,
        required_sections: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        required_sections = required_sections or [
            "search_intent_match",
            "topic_outline",
            "entity_coverage",
            "faq",
            "internal_link_opportunities",
            "conversion_path",
        ]
        seo_title = self._truncate(f"{title} | {topic.title()} SEO", 60)
        meta_description = self._truncate(
            f"Actionable {topic} guide for {primary_keyword}: intent mapping, structure, entities, and execution workflow.",
            160,
        )
        h2_outline = [
            f"{topic.title()} intent map",
            "SERP and competitor snapshot",
            "Content structure and schema plan",
            "Internal linking and hub navigation",
            "Measurement and iteration loop",
            "FAQ and implementation checklist",
        ]
        return {
            "slug": slug,
            "title": title,
            "seo_title": seo_title,
            "meta_description": meta_description,
            "schema_type": "Article",
            "template": template,
            "cluster": cluster,
            "target_word_count": target_word_count,
            "primary_keyword": primary_keyword,
            "secondary_keywords": [
                f"{primary_keyword} strategy",
                f"{primary_keyword} workflow",
                f"{primary_keyword} template",
            ],
            "h2_outline": h2_outline,
            "required_sections": required_sections,
            "recommended_anchors": [
                "intent map",
                "content framework",
                "schema plan",
                "measurement plan",
            ],
            "internal_links_from_this_page": [],
            "cta": f"Launch the {topic} execution workflow.",
        }

    def _build_seo_topics(
        self,
        root_slug: str,
        topic: str,
        target_topic_count: int,
        keyword_universe: List[Dict[str, Any]],
        spokes: List[Dict[str, Any]],
        app_matrix: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        topic_bases = [
            "intent clustering",
            "pillar and spoke planning",
            "on-page optimization",
            "technical seo checks",
            "schema entity coverage",
            "internal linking",
            "serp feature capture",
            "local seo expansion",
            "conversion pathway",
            "content refresh cadence",
            "analytics and iteration",
            "programmatic content operations",
        ]
        topic_bases.extend([row["service_name"].replace("_", " ") for row in app_matrix])

        topics: List[Dict[str, Any]] = []
        kw_count = len(keyword_universe)
        spoke_slugs = [s["slug"] for s in spokes] or [root_slug]
        for i in range(target_topic_count):
            base = topic_bases[i % len(topic_bases)]
            topic_id = f"topic-{i + 1}-{slugify(base)[:40]}"
            topic_name = f"{base.title()} for {topic.title()}"
            start = (i * 7) % kw_count
            topic_keywords = [keyword_universe[(start + j) % kw_count]["keyword"] for j in range(6)]
            subtopics = []
            for j in range(2):
                sub_kw = topic_keywords[j * 3 : (j + 1) * 3]
                subtopics.append(
                    {
                        "subtopic_id": f"subtopic-{j + 1}",
                        "subtopic_name": f"{base.title()} - Sprint {j + 1}",
                        "keyword_count": len(sub_kw),
                        "priority_keywords": sub_kw,
                        "mapped_pages": [
                            spoke_slugs[(i + j) % len(spoke_slugs)],
                            spoke_slugs[(i + j + 1) % len(spoke_slugs)],
                        ],
                    }
                )
            topics.append(
                {
                    "topic_id": topic_id,
                    "topic_name": topic_name,
                    "keyword_count": len(topic_keywords),
                    "priority_keywords": topic_keywords[:4],
                    "subtopics": subtopics,
                }
            )
        return topics

    def _build_seo_app_topic_keyword_map(
        self,
        app_matrix: List[Dict[str, Any]],
        topics: List[Dict[str, Any]],
        spokes: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        topic_ids = [topic["topic_id"] for topic in topics]
        topic_count = len(topics)
        rows: List[Dict[str, Any]] = []
        for idx, app in enumerate(app_matrix):
            route_count = min(6, topic_count)
            start = (idx * max(1, topic_count // max(1, len(app_matrix)))) % max(1, topic_count)
            selected_topics = [topics[(start + j) % topic_count] for j in range(route_count)]
            topic_routes = []
            for topic in selected_topics:
                topic_routes.append(
                    {
                        "topic_id": topic["topic_id"],
                        "topic_name": topic["topic_name"],
                        "keywords": topic["priority_keywords"],
                        "subtopics": [
                            {
                                "subtopic_id": sub["subtopic_id"],
                                "subtopic_name": sub["subtopic_name"],
                                "keywords": sub["priority_keywords"],
                            }
                            for sub in topic.get("subtopics", [])
                        ],
                    }
                )
            app_name = app["service_name"].replace("_", " ")
            linked_pages = [app["dedicated_page_slug"]]
            if spokes:
                linked_pages.extend([spokes[idx % len(spokes)]["slug"], spokes[(idx + 1) % len(spokes)]["slug"]])
            rows.append(
                {
                    "service_name": app["service_name"],
                    "service_page_slug": app["dedicated_page_slug"],
                    "topic_routes": topic_routes,
                    "linked_pages": linked_pages,
                    "keywords": [
                        f"{app_name} setup",
                        f"{app_name} workflow",
                        f"{app_name} automation",
                        f"{app_name} reporting",
                    ],
                    "required_sections": app.get("dedicated_sections", []),
                    "all_topic_ids": topic_ids,
                    "all_topic_count": topic_count,
                }
            )
        return rows

    def _build_seo_website_structure_tree(
        self,
        root_slug: str,
        site: Dict[str, Any],
        topics: List[Dict[str, Any]],
        app_matrix: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        spoke_pages = len(site.get("spokes", []))
        app_pages = len(app_matrix)
        topic_pages = len(topics)
        total_pages = 1 + spoke_pages + app_pages + topic_pages
        return {
            "page_inventory": {
                "pillar_pages": 1,
                "spoke_pages": spoke_pages,
                "service_pages": app_pages,
                "topic_hub_pages": topic_pages,
                "total_pages": total_pages,
            },
            "levels": {
                "level_1": [root_slug],
                "level_2": ["spokes", "apps", "topics", "templates"],
            },
        }

    def _build_seo_template_library(self, root_slug: str, topic: str) -> List[Dict[str, Any]]:
        return [
            {
                "template_id": "pillar_hub",
                "page_type": "pillar",
                "target_slug_pattern": root_slug,
                "required_blocks": ["bluf", "intent_map", "cluster_navigation", "faq", "cta"],
                "best_for": f"{topic} authority hubs",
            },
            {
                "template_id": "service_page",
                "page_type": "transactional",
                "target_slug_pattern": f"{root_slug}*/",
                "required_blocks": ["offer_summary", "proof", "pricing", "process", "cta"],
                "best_for": f"{topic} service queries",
            },
            {
                "template_id": "location_page",
                "page_type": "local",
                "target_slug_pattern": f"{root_slug}locations/*/",
                "required_blocks": ["location_intent", "local_proof", "service_area", "faq", "map"],
                "best_for": f"{topic} local landing pages",
            },
            {
                "template_id": "comparison_page",
                "page_type": "commercial",
                "target_slug_pattern": f"{root_slug}comparisons/*/",
                "required_blocks": ["criteria_table", "winner_by_use_case", "faq", "cta"],
                "best_for": f"{topic} vendor/tool comparisons",
            },
        ]

    def _build_seo_app_flows(self, root_slug: str, topic: str) -> List[Dict[str, Any]]:
        return [
            {
                "flow_id": "discovery_to_brief",
                "name": "Keyword Discovery to Content Brief",
                "owner_app": "keyword_research_app",
                "steps": [
                    "discover_keywords",
                    "cluster_intent",
                    "select_primary_secondary_terms",
                    "generate_content_brief",
                    "approve_and_publish_ticket",
                ],
                "primary_kpis": ["qualified_keywords", "brief_acceptance_rate"],
                "handoff_page": f"{root_slug}apps/content-brief-app/",
            },
            {
                "flow_id": "publish_to_index",
                "name": "Publishing and Indexation",
                "owner_app": "technical_audit_app",
                "steps": [
                    "validate_on_page_seo",
                    "inject_schema",
                    "publish_content",
                    "submit_indexing",
                    "verify_serp_presence",
                ],
                "primary_kpis": ["indexation_rate", "time_to_first_impression"],
                "handoff_page": f"{root_slug}apps/serp-tracking-app/",
            },
            {
                "flow_id": "measure_to_iteration",
                "name": "Performance Iteration Loop",
                "owner_app": "analytics_iteration_app",
                "steps": [
                    "collect_gsc_and_analytics",
                    "diagnose_underperforming_pages",
                    "prioritize_refresh_backlog",
                    "run_content_refresh",
                    "report_uplift",
                ],
                "primary_kpis": ["non_brand_click_growth", "refresh_win_rate"],
                "handoff_page": f"{root_slug}apps/analytics-iteration-app/",
            },
            {
                "flow_id": "local_expansion",
                "name": "Local SEO Expansion",
                "owner_app": "local_seo_app",
                "steps": [
                    "geo_keyword_mapping",
                    "build_location_templates",
                    "publish_location_pages",
                    "citation_sync",
                    "track_local_pack_changes",
                ],
                "primary_kpis": ["local_pack_visibility", "direction_calls_leads"],
                "handoff_page": f"{root_slug}apps/local-seo-app/",
            },
        ]

    def _build_keyword_rows(
        self,
        seed_keyword: str,
        target_count: int,
        include_questions: bool,
        repository_terms: Optional[Sequence[str]] = None,
        include_contract_defaults: bool = True,
    ) -> List[Dict[str, Any]]:
        repository_terms = repository_terms or []
        current_year = datetime.now(timezone.utc).year

        seed_terms: List[str] = []
        if include_contract_defaults:
            seed_terms.extend(
                [
                    "contract management",
                    "contract negotiation",
                    "vendor agreement",
                    "procurement contract",
                    "saas contracts",
                    "cost optimization",
                    "pricing governance",
                    "service level agreement",
                    "compliance contract",
                    "legal risk",
                    "api costs",
                    "seo service contracts",
                    "automation contracts",
                    "enterprise contracts",
                ]
            )
            seed_terms.extend([term.replace("_", " ") for term in self.DEFAULT_SERVICES])
        repo_slice = min(len(repository_terms), max(200, min(5000, target_count // 20)))
        seed_terms.extend(repository_terms[:repo_slice])

        unique_seed_terms: List[str] = []
        seen_seed_terms = set()
        for term in [seed_keyword] + seed_terms:
            normalized = self._normalize_keyword(term)
            if not normalized or normalized in seen_seed_terms:
                continue
            if include_contract_defaults and not self._is_domain_phrase(normalized):
                continue
            seen_seed_terms.add(normalized)
            unique_seed_terms.append(normalized)

        rows: List[Dict[str, Any]] = []
        seen = set()
        index = 0

        while len(rows) < target_count:
            intent = self.INTENTS[index % len(self.INTENTS)]
            modifier = self.INTENT_MODIFIERS[intent][index % len(self.INTENT_MODIFIERS[intent])]
            base = unique_seed_terms[index % len(unique_seed_terms)]
            variant = [
                f"{base} {modifier}",
                f"{base} {modifier} {current_year}",
                f"{modifier} for {base}",
                f"{base} {modifier} checklist",
                f"{base} {modifier} template",
                f"{base} {modifier} calculator",
            ][index % 6]

            if include_questions and index % 7 == 0:
                question_prefix = self.QUESTION_PREFIXES[index % len(self.QUESTION_PREFIXES)]
                variant = f"{question_prefix} {base} {modifier}"

            keyword = self._normalize_keyword(variant)
            if keyword in seen:
                # Deterministic fallback to prevent uniqueness exhaustion at large scales.
                keyword = self._normalize_keyword(f"{variant} set {index + 1}")

            if keyword:
                seen.add(keyword)
                rows.append(self._keyword_row(keyword=keyword, intent=intent, index=index))

            index += 1

        return rows

    def _keyword_row(self, keyword: str, intent: str, index: int) -> Dict[str, Any]:
        # Default mock metrics
        search_volume = max(30, 6500 - (index % 5200) + (len(keyword) % 170))
        competition = round(((index * 17) % 100) / 100, 2)
        difficulty = 18 + ((index * 13) % 72)
        cpc = round(0.5 + (((index * 19) % 500) / 100), 2)
        trend = "rising" if index % 3 == 0 else ("stable" if index % 3 == 1 else "seasonal")

        # Live API Hook (Google Custom Search API)
        if (
            getattr(self, "enable_live", False)
            and getattr(self, "google_api_key", None)
            and getattr(self, "google_search_engine_id", None)
        ):
            try:
                from src.api.google_search_client import GoogleSearchClient

                api = GoogleSearchClient(
                    api_key=self.google_api_key,
                    search_engine_id=self.google_search_engine_id,
                )
                meta = api.get_search_metadata(keyword)
                total_results = int(str(meta.get("total_results", "0")).replace(",", ""))

                # Conservative mapping from query breadth to SEO difficulty heuristics.
                if total_results > 0:
                    search_volume = max(30, min(100000, int(math.log10(total_results + 1) * 3500)))
                    competition = min(0.95, max(0.05, round(math.log10(total_results + 1) / 10, 2)))
                    difficulty = max(10, min(95, int(competition * 100)))
            except Exception:
                pass  # Fall back to mock on failure

        opportunity_score = round(
            (float(search_volume) / 120.0) * (1.15 - float(competition)) * (1.08 - (float(difficulty) / 100.0)),
            2,
        )

        return {
            "keyword": keyword,
            "search_volume": int(search_volume),
            "competition": float(competition),
            "difficulty": int(difficulty),
            "intent": intent,
            "cpc": float(cpc),
            "trend": trend,
            "opportunity_score": max(0.1, float(opportunity_score)),
        }

    def _build_site_structure(
        self,
        keyword_universe: List[Dict[str, Any]],
        coverage_matrix: List[Dict[str, Any]],
        max_spokes_per_cluster: int,
    ) -> Dict[str, Any]:
        pillar = {
            "title": "Costs and Contracts Knowledge Hub",
            "slug": "/resources/costs-contracts/",
            "primary_keyword": "costs and contracts",
            "target_word_count": 2600,
            "template": "pillar",
            "intent": "informational",
            "cluster": "core",
        }

        keywords_by_intent: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for row in keyword_universe:
            keywords_by_intent[row["intent"]].append(row)

        spokes: List[Dict[str, Any]] = []
        spoke_limit = max(2, max_spokes_per_cluster)
        for intent in self.INTENTS:
            candidates = sorted(
                keywords_by_intent.get(intent, []),
                key=lambda item: item["opportunity_score"],
                reverse=True,
            )[:spoke_limit]
            for idx, item in enumerate(candidates):
                raw_slug = slugify(item["keyword"])
                slug = f"/resources/costs-contracts/{raw_slug}/"
                spokes.append(
                    {
                        "slug": slug,
                        "title": item["keyword"].title(),
                        "primary_keyword": item["keyword"],
                        "intent": intent,
                        "template": self._template_for_intent(intent),
                        "cluster": f"{intent}-cluster",
                        "target_word_count": 1400 + (idx * 80),
                    }
                )

        while len(spokes) < 8:
            idx = len(spokes)
            kw = keyword_universe[idx % len(keyword_universe)]
            slug = f"/resources/costs-contracts/{slugify(kw['keyword'])}-{idx + 1}/"
            spokes.append(
                {
                    "slug": slug,
                    "title": kw["keyword"].title(),
                    "primary_keyword": kw["keyword"],
                    "intent": kw["intent"],
                    "template": self._template_for_intent(kw["intent"]),
                    "cluster": f"{kw['intent']}-cluster",
                    "target_word_count": 1500,
                }
            )

        unique_spokes: List[Dict[str, Any]] = []
        seen_slugs = set()
        for row in spokes:
            if row["slug"] in seen_slugs:
                continue
            seen_slugs.add(row["slug"])
            unique_spokes.append(row)
        spokes = unique_spokes

        page_briefs: Dict[str, Dict[str, Any]] = {}
        page_briefs[pillar["slug"]] = self._build_page_brief(
            slug=pillar["slug"],
            title=pillar["title"],
            primary_keyword=pillar["primary_keyword"],
            template="pillar",
            cluster="core",
            target_word_count=pillar["target_word_count"],
        )

        for spoke in spokes:
            page_briefs[spoke["slug"]] = self._build_page_brief(
                slug=spoke["slug"],
                title=spoke["title"],
                primary_keyword=spoke["primary_keyword"],
                template=spoke["template"],
                cluster=spoke["cluster"],
                target_word_count=spoke["target_word_count"],
            )

        coverage_page_briefs = {}
        for row in coverage_matrix:
            coverage_page_briefs[row["dedicated_page_slug"]] = self._build_page_brief(
                slug=row["dedicated_page_slug"],
                title=f"{row['service_name'].replace('_', ' ').title()} Cost and Contract Guide",
                primary_keyword=f"{row['service_name'].replace('_', ' ')} contract cost",
                template="service_coverage",
                cluster="service-coverage",
                target_word_count=1600,
                required_sections=row["dedicated_sections"],
            )

        internal_links = self._build_internal_links(pillar_slug=pillar["slug"], spokes=spokes)
        self._attach_links_to_briefs(page_briefs, internal_links)
        self._attach_links_to_briefs(coverage_page_briefs, internal_links)

        outlines = {
            slug: {
                "title": brief["title"],
                "h2_outline": brief["h2_outline"],
            }
            for slug, brief in {**page_briefs, **coverage_page_briefs}.items()
        }

        return {
            "pillar": pillar,
            "spokes": spokes,
            "internal_links": internal_links,
            "page_briefs": page_briefs,
            "coverage_page_briefs": coverage_page_briefs,
            "outlines": outlines,
        }

    def _template_for_intent(self, intent: str) -> str:
        if intent == "transactional":
            return "service_page"
        if intent == "commercial":
            return "comparison"
        if intent == "navigational":
            return "integration_guide"
        return "article"

    def _build_page_brief(
        self,
        slug: str,
        title: str,
        primary_keyword: str,
        template: str,
        cluster: str,
        target_word_count: int,
        required_sections: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        required_sections = required_sections or [
            "pricing_breakdown",
            "contract_risk_notes",
            "vendor_comparison_or_checklist",
            "faq",
            "implementation_steps",
        ]

        seo_title = self._truncate(f"{title} | Costs and Contracts", 60)
        meta_description = self._truncate(
            f"Structured guide to {primary_keyword}: pricing, contract clauses, risks, and implementation decisions.",
            160,
        )

        h2_outline = [
            "Cost model overview",
            "Contract clause breakdown",
            "Risk and compliance controls",
            "Implementation and governance workflow",
            "Vendor comparison and selection criteria",
            "FAQ for procurement and legal teams",
        ]

        return {
            "slug": slug,
            "title": title,
            "seo_title": seo_title,
            "meta_description": meta_description,
            "schema_type": "Article",
            "template": template,
            "cluster": cluster,
            "target_word_count": target_word_count,
            "primary_keyword": primary_keyword,
            "secondary_keywords": [
                f"{primary_keyword} pricing",
                f"{primary_keyword} contract terms",
                f"{primary_keyword} implementation cost",
            ],
            "h2_outline": h2_outline,
            "required_sections": required_sections,
            "recommended_anchors": [
                "cost breakdown",
                "contract clauses",
                "risk controls",
                "implementation plan",
            ],
            "internal_links_from_this_page": [],
            "cta": "Request a structured cost and contract assessment.",
        }

    def _build_internal_links(self, pillar_slug: str, spokes: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        links: List[Dict[str, str]] = []
        for spoke in spokes:
            links.append({"from": pillar_slug, "to": spoke["slug"], "type": "hub_to_spoke"})
            links.append({"from": spoke["slug"], "to": pillar_slug, "type": "spoke_to_hub"})

        cluster_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for spoke in spokes:
            cluster_map[spoke["cluster"]].append(spoke)

        for cluster_rows in cluster_map.values():
            for idx, row in enumerate(cluster_rows):
                if len(cluster_rows) < 2:
                    continue
                target = cluster_rows[(idx + 1) % len(cluster_rows)]
                if row["slug"] != target["slug"]:
                    links.append({"from": row["slug"], "to": target["slug"], "type": "cluster_crosslink"})

        deduped = {}
        for link in links:
            key = (link["from"], link["to"], link["type"])
            deduped[key] = link
        return list(deduped.values())

    def _attach_links_to_briefs(self, briefs: Dict[str, Dict[str, Any]], links: List[Dict[str, str]]) -> None:
        by_source: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        for link in links:
            by_source[link["from"]].append(link)
        for slug, brief in briefs.items():
            brief["internal_links_from_this_page"] = by_source.get(slug, [])

    def _load_services_catalog(self) -> Dict[str, Any]:
        services_yaml = self._load_yaml(self.repo_root / "services.yaml")
        cost_yaml = self._load_yaml(self.repo_root / "cost_model.yaml")
        return {
            "services": services_yaml.get("services", {}),
            "costs": cost_yaml.get("services", {}),
        }

    def _build_coverage_matrix(self, catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
        services_cfg = catalog.get("services", {})
        costs_cfg = catalog.get("costs", {})
        all_names = sorted(set(self.DEFAULT_SERVICES) | set(services_cfg.keys()) | set(costs_cfg.keys()))

        rows = []
        for name in all_names:
            service_slug = slugify(name.replace("_", " "))
            rows.append(
                {
                    "service_name": name,
                    "in_services_yaml": name in services_cfg,
                    "in_cost_model_yaml": name in costs_cfg,
                    "dedicated_page_slug": f"/resources/costs-contracts/services/{service_slug}/",
                    "dedicated_sections": [
                        "overview",
                        "pricing_breakdown",
                        "contract_terms",
                        "risk_and_compliance",
                        "sla_and_support",
                        "implementation_steps",
                    ],
                }
            )
        return rows

    def _build_topics(
        self,
        target_topic_count: int,
        keyword_universe: List[Dict[str, Any]],
        spokes: List[Dict[str, Any]],
        coverage_matrix: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        topic_bases = [
            "vendor selection",
            "procurement governance",
            "legal operations",
            "compliance assurance",
            "renewal strategy",
            "termination readiness",
            "indemnity management",
            "budget forecasting",
            "implementation planning",
            "service-level controls",
            "data protection",
            "audit evidence",
            "pricing analytics",
            "roi modeling",
            "risk scoring",
            "contract lifecycle",
        ]
        topic_bases.extend([row["service_name"].replace("_", " ") for row in coverage_matrix])

        topics: List[Dict[str, Any]] = []
        kw_count = len(keyword_universe)
        spoke_slugs = [s["slug"] for s in spokes] or ["/resources/costs-contracts/"]

        for i in range(target_topic_count):
            base = topic_bases[i % len(topic_bases)]
            topic_id = f"topic-{i + 1}-{slugify(base)[:40]}"
            topic_name = f"{base.title()} Cost and Contract Strategy"

            start = (i * 7) % kw_count
            topic_keywords = [keyword_universe[(start + j) % kw_count]["keyword"] for j in range(6)]

            subtopics = []
            for j in range(2):
                sub_kw = topic_keywords[j * 3 : (j + 1) * 3]
                subtopics.append(
                    {
                        "subtopic_id": f"subtopic-{j + 1}",
                        "subtopic_name": f"{base.title()} - Workstream {j + 1}",
                        "keyword_count": len(sub_kw),
                        "priority_keywords": sub_kw,
                        "mapped_pages": [
                            spoke_slugs[(i + j) % len(spoke_slugs)],
                            spoke_slugs[(i + j + 1) % len(spoke_slugs)],
                        ],
                    }
                )

            topics.append(
                {
                    "topic_id": topic_id,
                    "topic_name": topic_name,
                    "keyword_count": len(topic_keywords),
                    "priority_keywords": topic_keywords[:4],
                    "subtopics": subtopics,
                }
            )

        return topics

    def _build_keyword_framework(self, keyword_universe: List[Dict[str, Any]]) -> Dict[str, Any]:
        head_terms = []
        mid_tail = []
        long_tail = []
        question_terms = []
        intent_buckets: Dict[str, List[str]] = defaultdict(list)

        for row in keyword_universe:
            kw = row["keyword"]
            word_len = len(kw.split())
            if word_len <= 2 and len(head_terms) < 3000:
                head_terms.append(kw)
            elif 3 <= word_len <= 4 and len(mid_tail) < 6000:
                mid_tail.append(kw)
            elif len(long_tail) < 12000:
                long_tail.append(kw)

            if kw.startswith(("how ", "what ", "why ", "when ", "which ")) and len(question_terms) < 6000:
                question_terms.append(kw)

            intent = row.get("intent", "informational")
            if len(intent_buckets[intent]) < 15000:
                intent_buckets[intent].append(kw)

        return {
            "head_terms": head_terms,
            "mid_tail_terms": mid_tail,
            "long_tail_terms": long_tail,
            "question_terms": question_terms,
            "intent_buckets": intent_buckets,
        }

    def _build_service_page_topic_keyword_map(
        self,
        coverage_matrix: List[Dict[str, Any]],
        topics: List[Dict[str, Any]],
        spokes: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        topic_ids = [topic["topic_id"] for topic in topics]
        topic_count = len(topics)

        rows = []
        for idx, service in enumerate(coverage_matrix):
            route_count = min(8, topic_count)
            start = (idx * max(1, topic_count // max(1, len(coverage_matrix)))) % max(1, topic_count)
            selected_topics = [topics[(start + j) % topic_count] for j in range(route_count)]

            topic_routes = []
            for topic in selected_topics:
                topic_routes.append(
                    {
                        "topic_id": topic["topic_id"],
                        "topic_name": topic["topic_name"],
                        "keywords": topic["priority_keywords"],
                        "subtopics": [
                            {
                                "subtopic_id": sub["subtopic_id"],
                                "subtopic_name": sub["subtopic_name"],
                                "keywords": sub["priority_keywords"],
                            }
                            for sub in topic.get("subtopics", [])
                        ],
                    }
                )

            keywords = [
                f"{service['service_name'].replace('_', ' ')} pricing",
                f"{service['service_name'].replace('_', ' ')} contract terms",
                f"{service['service_name'].replace('_', ' ')} implementation cost",
                f"{service['service_name'].replace('_', ' ')} compliance requirements",
            ]

            linked_pages = [service["dedicated_page_slug"]]
            if spokes:
                linked_pages.append(spokes[idx % len(spokes)]["slug"])
                linked_pages.append(spokes[(idx + 1) % len(spokes)]["slug"])

            rows.append(
                {
                    "service_name": service["service_name"],
                    "service_page_slug": service["dedicated_page_slug"],
                    "topic_routes": topic_routes,
                    "linked_pages": linked_pages,
                    "keywords": keywords,
                    "required_sections": service.get("dedicated_sections", []),
                    "all_topic_ids": topic_ids,
                    "all_topic_count": topic_count,
                }
            )

        return rows

    def _build_website_structure_tree(
        self,
        site: Dict[str, Any],
        topics: List[Dict[str, Any]],
        coverage_matrix: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        spoke_pages = len(site.get("spokes", []))
        coverage_pages = len(coverage_matrix)
        topic_pages = len(topics)
        total_pages = 1 + spoke_pages + coverage_pages + topic_pages

        return {
            "page_inventory": {
                "pillar_pages": 1,
                "spoke_pages": spoke_pages,
                "service_pages": coverage_pages,
                "topic_hub_pages": topic_pages,
                "total_pages": total_pages,
            },
            "levels": {
                "level_1": ["/resources/costs-contracts/"],
                "level_2": ["spokes", "services", "topics"],
            },
        }

    def _evaluate_quality(
        self,
        keyword_universe: List[Dict[str, Any]],
        topics: List[Dict[str, Any]],
        service_map: List[Dict[str, Any]],
        coverage_matrix: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        errors = []
        warnings = []

        if len(keyword_universe) < 300:
            errors.append("keyword_universe_below_minimum")
        if len(topics) < 12:
            errors.append("topic_count_below_minimum")
        if not service_map:
            errors.append("service_map_missing")
        if not coverage_matrix:
            errors.append("coverage_matrix_missing")

        duplicate_keywords = self._count_duplicate_keywords(keyword_universe)
        if duplicate_keywords > 0:
            warnings.append(f"duplicate_keywords:{duplicate_keywords}")

        return {
            "passed": len(errors) == 0,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors,
            "warnings": warnings,
        }

    def _count_duplicate_keywords(self, rows: List[Dict[str, Any]]) -> int:
        counts = Counter(self._normalize_keyword(row.get("keyword", "")) for row in rows)
        return sum(v - 1 for v in counts.values() if v > 1)

    def _scan_repository_terms(self, max_repository_terms: int) -> Tuple[List[str], Dict[str, Any]]:
        cached = self._repository_scan_cache.get(max_repository_terms)
        if cached is not None:
            terms, inventory = cached
            cached_inventory = dict(inventory)
            cached_inventory["cache_hit"] = True
            return list(terms), cached_inventory

        considered_files = 0
        scanned_files = 0
        extracted_terms = Counter()

        root = self.repo_root
        repo_metadata = self._detect_repo_metadata(root)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in self.SKIP_DIR_NAMES]
            for filename in filenames:
                considered_files += 1
                path = Path(dirpath) / filename

                if path.suffix.lower() not in self.REPO_FILE_SUFFIXES:
                    continue
                try:
                    if path.stat().st_size > 1_500_000:
                        continue
                except OSError:
                    continue

                scanned_files += 1

                extracted_terms.update(self._tokenize(path.stem))

                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue

                extracted_terms.update(self._tokenize(text[:4000]))

        ranked_terms = [term for term, _count in extracted_terms.most_common(max_repository_terms * 3)]
        domain_terms = [term for term in ranked_terms if self._is_domain_phrase(term)]
        fallback_terms = [term for term in ranked_terms if term not in domain_terms]
        top_terms = domain_terms[:max_repository_terms]
        if len(top_terms) < max_repository_terms:
            needed = max_repository_terms - len(top_terms)
            top_terms.extend(fallback_terms[:needed])

        inventory = {
            "scan_scope": "repository_root_recursive",
            "root_path": str(root),
            "repo_metadata": repo_metadata,
            "considered_files": considered_files,
            "scanned_files": scanned_files,
            "extracted_terms_count": len(top_terms),
            "max_repository_terms": max_repository_terms,
            "cache_hit": False,
        }
        self._repository_scan_cache[max_repository_terms] = (list(top_terms), dict(inventory))
        return top_terms, inventory

    def _detect_repo_metadata(self, root: Path) -> Dict[str, Any]:
        git_dir = root / ".git"
        if git_dir.is_dir():
            return {"type": "git", "present": True}
        if git_dir.is_file():
            return {"type": "git_worktree", "present": True}
        return {"type": "filesystem_only", "present": False}

    def _tokenize(self, text: str) -> List[str]:
        raw_tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_\-]{2,}", text.lower())
        tokens = []
        for token in raw_tokens:
            token = token.strip("_-")
            if len(token) < 3:
                continue
            if token in self.STOPWORDS:
                continue
            if token.isdigit():
                continue
            tokens.append(token)
        return tokens

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def _normalize_keyword(self, term: str) -> str:
        line = term.strip().lower()
        line = re.sub(r"\s+", " ", line)
        return line

    def _is_domain_phrase(self, phrase: str) -> bool:
        words = re.findall(r"[a-z0-9]+", phrase.lower())
        if not words:
            return False
        for word in words:
            if word in self.DOMAIN_ROOTS:
                return True
            for root in self.DOMAIN_ROOTS:
                if word.startswith(root):
                    return True
        return False

    def _truncate(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        short = text[: limit - 3].rstrip()
        return f"{short}..."
