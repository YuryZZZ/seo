"""Tests for the InternalLinker — relevance scoring, anchor text, link graph, orphan detection."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import pytest
from internal_linker import InternalLinker, LinkOpportunity


# ── Fixtures ────────────────────────────────────────────────────────────────

ARTICLES = [
    {
        "url": "/seo-guide",
        "title": "Complete SEO Guide",
        "keywords": ["seo", "search engine optimization", "rankings"],
        "content": "This is a complete guide to SEO and search engine optimization for rankings.",
    },
    {
        "url": "/keyword-research",
        "title": "Keyword Research Tips",
        "keywords": ["keyword research", "keywords", "search intent"],
        "content": "Keyword research is the foundation of SEO. Understanding search intent is crucial.",
    },
    {
        "url": "/link-building",
        "title": "Link Building Strategies",
        "keywords": ["link building", "backlinks", "authority"],
        "content": "Link building helps improve authority through high-quality backlinks.",
    },
    {
        "url": "/technical-seo",
        "title": "Technical SEO Checklist",
        "keywords": ["technical seo", "site speed", "crawlability"],
        "content": "Technical SEO covers site speed optimization and crawlability improvements.",
    },
]

CONTENT_ABOUT_SEO = """
This article discusses comprehensive SEO strategies including keyword research,
link building best practices, and search engine optimization techniques.
We cover search intent analysis, technical seo audits, and authority building.
"""


# ── Tests ───────────────────────────────────────────────────────────────────

class TestLinkOpportunity:
    """Test the LinkOpportunity data class."""

    def test_to_dict(self):
        op = LinkOpportunity(
            source_url="/page-a",
            target_url="/page-b",
            target_title="Page B",
            anchor_text="page b content",
            relevance_score=0.7531,
        )
        d = op.to_dict()
        assert d["source_url"] == "/page-a"
        assert d["target_url"] == "/page-b"
        assert d["relevance_score"] == 0.753  # rounded to 3

    def test_default_position(self):
        op = LinkOpportunity("", "", "", "")
        assert op.position == "body"


class TestSuggestLinks:
    """Test link suggestion engine."""

    def test_empty_content_returns_empty(self):
        linker = InternalLinker()
        assert linker.suggest_links("", ARTICLES) == []

    def test_empty_articles_returns_empty(self):
        linker = InternalLinker()
        assert linker.suggest_links("some content", []) == []

    def test_returns_relevant_links(self):
        linker = InternalLinker()
        results = linker.suggest_links(CONTENT_ABOUT_SEO, ARTICLES)
        assert len(results) > 0
        # Should find keyword-matching articles
        urls = [r["url"] for r in results]
        assert "/seo-guide" in urls or "/keyword-research" in urls

    def test_avoids_self_links(self):
        linker = InternalLinker()
        results = linker.suggest_links(
            CONTENT_ABOUT_SEO, ARTICLES, current_url="/seo-guide"
        )
        urls = [r["url"] for r in results]
        assert "/seo-guide" not in urls

    def test_respects_max_links(self):
        linker = InternalLinker(max_links_per_page=2)
        results = linker.suggest_links(CONTENT_ABOUT_SEO, ARTICLES)
        assert len(results) <= 2

    def test_sorted_by_relevance(self):
        linker = InternalLinker()
        results = linker.suggest_links(CONTENT_ABOUT_SEO, ARTICLES)
        if len(results) >= 2:
            scores = [r["score"] for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_includes_anchor_text(self):
        linker = InternalLinker()
        results = linker.suggest_links(CONTENT_ABOUT_SEO, ARTICLES)
        for r in results:
            assert "anchor_text" in r
            assert len(r["anchor_text"]) > 0

    def test_min_relevance_threshold(self):
        linker = InternalLinker(min_relevance_score=0.99)
        results = linker.suggest_links("just random text", ARTICLES)
        assert len(results) == 0

    def test_no_duplicate_urls(self):
        linker = InternalLinker()
        # Duplicate articles
        duped = ARTICLES + [ARTICLES[0]]
        results = linker.suggest_links(CONTENT_ABOUT_SEO, duped)
        urls = [r["url"] for r in results]
        assert len(urls) == len(set(urls))


class TestRelevanceScoring:
    """Test the internal relevance calculation."""

    def test_empty_keywords_title_match(self):
        linker = InternalLinker()
        content = "read our complete seo guide today"
        score, anchor = linker._calculate_relevance(content, [], "complete seo guide")
        assert score > 0
        assert anchor == "complete seo guide"

    def test_empty_keywords_no_title_match(self):
        linker = InternalLinker()
        score, anchor = linker._calculate_relevance("unrelated", [], "seo guide")
        assert score == 0.0

    def test_keyword_frequency_increases_score(self):
        linker = InternalLinker()
        # One mention
        s1, _ = linker._calculate_relevance("seo is great", ["seo"], "")
        # Multiple mentions
        s2, _ = linker._calculate_relevance("seo is seo and more seo", ["seo"], "")
        assert s2 >= s1

    def test_longer_keywords_get_bonus(self):
        linker = InternalLinker()
        s1, _ = linker._calculate_relevance(
            "search engine optimization", ["search"], ""
        )
        s2, _ = linker._calculate_relevance(
            "search engine optimization", ["search engine optimization"], ""
        )
        assert s2 > s1

    def test_early_mention_bonus(self):
        linker = InternalLinker()
        # Keyword in first 500 chars
        early = "seo" + " " * 600 + "end"
        late = " " * 600 + "seo"
        s1, _ = linker._calculate_relevance(early, ["seo"], "")
        s2, _ = linker._calculate_relevance(late, ["seo"], "")
        assert s1 > s2


class TestLinkGraph:
    """Test link graph construction."""

    def test_builds_graph(self):
        linker = InternalLinker()
        graph = linker.build_link_graph(ARTICLES)
        assert isinstance(graph, dict)
        # At least one page should link to others
        assert any(len(targets) > 0 for targets in graph.values())

    def test_no_self_links_in_graph(self):
        linker = InternalLinker()
        graph = linker.build_link_graph(ARTICLES)
        for source, targets in graph.items():
            assert source not in targets


class TestOrphanPages:
    """Test orphan page detection."""

    def test_finds_orphans(self):
        linker = InternalLinker(min_relevance_score=0.99)  # Very high threshold
        articles = [
            {"url": "/a", "content": "unrelated content", "keywords": ["xyz"]},
            {"url": "/b", "content": "other content", "keywords": ["abc"]},
        ]
        orphans = linker.find_orphan_pages(articles)
        # With high threshold, both should be orphans (no links to each other)
        assert len(orphans) == 2

    def test_empty_articles(self):
        linker = InternalLinker()
        assert linker.find_orphan_pages([]) == []
