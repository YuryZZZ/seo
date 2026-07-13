"""Tests for keyword researcher and costs/contracts site structure package."""

from pathlib import Path

from src.keyword_researcher import KeywordResearcher


def test_research_keywords_returns_clustered_report():
    researcher = KeywordResearcher()
    report = researcher.research_keywords("contract management costs", limit=15)

    assert report["seed_keyword"] == "contract management costs"
    assert report["total_keywords"] > 0
    assert isinstance(report["clusters"], dict)
    assert isinstance(report["top_opportunities"], list)
    assert len(report["top_opportunities"]) > 0


def test_build_costs_contracts_framework_has_pillar_and_spokes():
    researcher = KeywordResearcher()
    package = researcher.build_costs_contracts_framework(base_url="https://example.com")

    assert package["topic"] == "costs and contracts"
    site = package["site_structure"]
    assert site["pillar"]["slug"] == "/resources/costs-contracts/"
    assert len(site["spokes"]) >= 8

    slugs = [site["pillar"]["slug"]] + [s["slug"] for s in site["spokes"]]
    assert len(slugs) == len(set(slugs))
    assert all(slug.startswith("/resources/costs-contracts/") for slug in slugs)

    intents = {spoke["intent"] for spoke in site["spokes"]}
    assert "informational" in intents or "commercial" in intents or "transactional" in intents
    assert package["quality_gates"]["passed"] is True


def test_internal_links_include_hub_to_spoke_and_spoke_to_hub():
    researcher = KeywordResearcher()
    package = researcher.build_costs_contracts_framework(base_url="https://example.com")

    links = package["site_structure"]["internal_links"]
    link_types = {link["type"] for link in links}
    assert "hub_to_spoke" in link_types
    assert "spoke_to_hub" in link_types


def test_publish_ready_briefs_have_required_fields_and_lengths():
    researcher = KeywordResearcher()
    package = researcher.build_costs_contracts_framework(base_url="https://example.com")
    briefs = package["site_structure"]["page_briefs"]

    assert briefs
    for slug, brief in briefs.items():
        assert brief["slug"] == slug
        assert len(brief["seo_title"]) <= 60
        assert len(brief["meta_description"]) <= 160
        assert len(brief["h2_outline"]) >= 5
        for required in [
            "pricing_breakdown",
            "contract_risk_notes",
            "vendor_comparison_or_checklist",
            "faq",
        ]:
            assert required in brief["required_sections"]


def test_coverage_matrix_includes_all_known_services():
    researcher = KeywordResearcher()
    package = researcher.build_costs_contracts_framework(base_url="https://example.com")
    matrix = package["coverage_matrix"]
    service_names = {row["service_name"] for row in matrix}
    expected = {
        "taskbus_postgres",
        "google_search_console",
        "google_custom_search",
        "brave_search",
        "tavily_search",
        "perplexity_search",
        "glm_search",
        "youtube_data_api",
    }
    assert expected.issubset(service_names)
    for row in matrix:
        assert row["dedicated_page_slug"].startswith("/resources/costs-contracts/")
        assert len(row["dedicated_sections"]) >= 4


def test_outlines_include_cost_or_contract_terminology():
    researcher = KeywordResearcher()
    package = researcher.build_costs_contracts_framework(base_url="https://example.com")
    outlines = package["site_structure"]["outlines"]

    for outline in outlines.values():
        joined = " ".join(outline["h2_outline"]).lower()
        assert ("cost" in joined) or ("contract" in joined)


def test_research_dossier_contains_topics_subtopics_and_keyword_framework():
    researcher = KeywordResearcher()
    package = researcher.build_costs_contracts_framework(base_url="https://example.com")

    dossier = package["research_dossier"]
    assert dossier["site_structure_summary"]["cms"] == "framework-native (no wordpress dependency)"
    assert dossier["site_structure_summary"]["topic_count"] >= 12
    assert dossier["site_structure_summary"]["keyword_count"] >= 300
    assert dossier["repository_scan_inventory"]["scan_scope"] == "repository_root_recursive"
    assert dossier["repository_scan_inventory"]["scanned_files"] > 0

    topics = dossier["topics"]
    assert topics
    assert all(topic["priority_keywords"] for topic in topics)
    assert any(topic["subtopics"] for topic in topics)

    framework = dossier["keyword_framework"]
    assert "head_terms" in framework
    assert "mid_tail_terms" in framework
    assert "long_tail_terms" in framework
    assert "intent_buckets" in framework

    service_map = dossier["service_page_topic_keyword_map"]
    assert service_map
    for row in service_map:
        assert row["service_page_slug"].startswith("/resources/costs-contracts/")
        assert row["topic_routes"]
        assert row["keywords"]


def test_build_costs_contracts_framework_respects_requested_sizes():
    researcher = KeywordResearcher()
    package = researcher.build_costs_contracts_framework(
        base_url="https://example.com",
        target_keyword_count=640,
        target_topic_count=72,
    )

    assert len(package["keyword_universe"]) == 640
    assert len(package["research_dossier"]["topics"]) == 72
    assert package["research_dossier"]["site_structure_summary"]["keyword_count"] == 640
    assert package["research_dossier"]["site_structure_summary"]["topic_count"] == 72


def test_framework_page_inventory_matches_generated_sections():
    researcher = KeywordResearcher()
    package = researcher.build_costs_contracts_framework(base_url="https://example.com")

    site = package["site_structure"]
    dossier = package["research_dossier"]
    inventory = dossier["website_structure_tree"]["page_inventory"]

    assert inventory["pillar_pages"] == 1
    assert inventory["spoke_pages"] == len(site["spokes"])
    assert inventory["service_pages"] == len(package["coverage_matrix"])
    assert inventory["topic_hub_pages"] == len(dossier["topics"])
    assert inventory["total_pages"] == (
        inventory["pillar_pages"]
        + inventory["spoke_pages"]
        + inventory["service_pages"]
        + inventory["topic_hub_pages"]
    )


def test_repository_scan_inventory_reports_non_git_workspace(tmp_path: Path):
    (tmp_path / "services.yaml").write_text("services: {}\n", encoding="utf-8")
    (tmp_path / "cost_model.yaml").write_text("services: {}\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("contract pricing governance audit\n", encoding="utf-8")

    researcher = KeywordResearcher(repo_root=tmp_path)
    package = researcher.build_costs_contracts_framework(
        base_url="https://example.com",
        max_repository_terms=20,
        target_keyword_count=300,
        target_topic_count=12,
    )

    repo_metadata = package["repository_scan_inventory"]["repo_metadata"]
    assert repo_metadata == {"type": "filesystem_only", "present": False}
    assert package["repository_scan_inventory"]["cache_hit"] is False


def test_repository_scan_inventory_uses_cached_terms_on_repeat_calls(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "services.yaml").write_text("services: {}\n", encoding="utf-8")
    (tmp_path / "cost_model.yaml").write_text("services: {}\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("contract pricing governance audit\n", encoding="utf-8")

    researcher = KeywordResearcher(repo_root=tmp_path)
    first = researcher.build_costs_contracts_framework(
        base_url="https://example.com",
        max_repository_terms=21,
        target_keyword_count=300,
        target_topic_count=12,
    )
    second = researcher.build_costs_contracts_framework(
        base_url="https://example.com",
        max_repository_terms=21,
        target_keyword_count=300,
        target_topic_count=12,
    )

    assert first["repository_scan_inventory"]["repo_metadata"] == {"type": "git", "present": True}
    assert first["repository_scan_inventory"]["cache_hit"] is False
    assert second["repository_scan_inventory"]["cache_hit"] is True
    assert second["research_dossier"]["repository_signal_topics"] == first["research_dossier"]["repository_signal_topics"]


def test_google_custom_search_keyword_enrichment(monkeypatch):
    from unittest.mock import MagicMock
    
    # Mock GoogleCustomSearchAPI search response
    mock_search = MagicMock(return_value={
        "status": "ok",
        "query": "contract management",
        "data": {
            "items": [
                {"title": "Contract Management Software Pricing", "snippet": "Compare the best tools"},
                {"title": "Standard Legal Agreement Clause templates", "snippet": "Learn about contract risk and liability rules"}
            ]
        }
    })
    
    # Patch GoogleCustomSearchAPI class
    try:
        from src.apis.google_custom_search import GoogleCustomSearchAPI
    except ImportError:
        from apis.google_custom_search import GoogleCustomSearchAPI
        
    monkeypatch.setattr(GoogleCustomSearchAPI, "search", mock_search)
    
    researcher = KeywordResearcher(config={
        "google_api_key": "dummy_key",
        "google_search_engine_id": "dummy_cx"
    })
    
    report = researcher.research_keywords("contract management", limit=10)
    
    assert report["google_enriched"] > 0
    # Verify mock was called
    mock_search.assert_called_once()

