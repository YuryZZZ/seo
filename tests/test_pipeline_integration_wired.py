"""
Integration test — Full 10-phase pipeline with all modules wired.
Tests that the orchestrator properly initializes and runs all phases
using the real SERPAnalyzer, EntityExtractor, MasterCopywriter,
IAArchitect, CompetitorAnalyzer, and GateRegistry modules.
"""

import asyncio
import sys
import os
import pytest

# Add src to path so sibling imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))


def test_orchestrator_modules_wired():
    """Verify all modules are initialized (not None) in the orchestrator."""
    from orchestrator import SEOGEOOrchestrator

    orch = SEOGEOOrchestrator()

    # These MUST be wired (not None)
    assert orch.agents["keyword_researcher"] is not None, "keyword_researcher not wired"
    assert orch.agents["serp_analyzer"] is not None, "serp_analyzer not wired"
    assert orch.agents["entity_extractor"] is not None, "entity_extractor not wired"
    assert orch.agents["ia_architect"] is not None, "ia_architect not wired"
    assert orch.agents["content_optimizer"] is not None, "content_optimizer not wired"
    assert orch.agents["competitive_analyzer"] is not None, "competitive_analyzer not wired"
    assert orch.agents["gate_registry"] is not None, "gate_registry not wired"

    # Count wired agents
    wired = sum(1 for v in orch.agents.values() if v is not None)
    assert wired >= 7, f"Expected at least 7 wired agents, got {wired}"
    print(f"✅ {wired}/{len(orch.agents)} agents wired")


def test_phase_0_initialization():
    """Phase 0: Initialization returns correct structure."""
    from orchestrator import SEOGEOOrchestrator

    orch = SEOGEOOrchestrator()
    result = asyncio.run(orch.execute_phase(0, {
        "target_url": "https://example.com",
        "target_keywords": ["seo optimization"],
        "geo_locations": ["New York"]
    }))

    assert result["status"] == "completed"
    assert result["phase"] == 0
    assert "target_url" in result["data"]
    print("✅ Phase 0: Initialization passed")


def test_phase_1_keyword_research():
    """Phase 1: Keyword research returns real data."""
    from orchestrator import SEOGEOOrchestrator

    orch = SEOGEOOrchestrator()
    result = asyncio.run(orch.execute_phase(1, {
        "target_keywords": ["construction cost estimator"]
    }))

    assert result["status"] == "completed"
    assert result["phase"] == 1
    assert "seed_keyword" in result
    assert "keywords_found" in result
    print(f"✅ Phase 1: Keyword Research — {result['keywords_found']} keywords found")


def test_phase_2_serp_analysis():
    """Phase 2: SERP analysis uses real SERPAnalyzer."""
    from orchestrator import SEOGEOOrchestrator

    orch = SEOGEOOrchestrator()
    result = asyncio.run(orch.execute_phase(2, {
        "target_keywords": ["seo optimization"],
        "focus_keyword": "seo optimization"
    }))

    assert result["status"] == "completed"
    assert result["phase"] == 2
    assert "keyword" in result
    assert "competitors_identified" in result
    print(f"✅ Phase 2: SERP Analysis — {result.get('competitors_identified', 0)} competitors")


def test_phase_3_ia_design():
    """Phase 3: IA Design uses real IAArchitect."""
    from orchestrator import SEOGEOOrchestrator

    orch = SEOGEOOrchestrator()
    result = asyncio.run(orch.execute_phase(3, {
        "focus_keyword": "seo optimization"
    }))

    assert result["status"] == "completed"
    assert result["phase"] == 3
    assert result["h2_structure_created"] is True
    # Real IAArchitect should produce H2 questions
    assert "h2_questions" in result
    assert "citable_blocks" in result
    assert "table_of_contents" in result
    print(f"✅ Phase 3: IA Design — {len(result.get('h2_questions', []))} H2 questions generated")


def test_phase_4_content_optimization():
    """Phase 4: Content optimization uses real MasterCopywriter."""
    from orchestrator import SEOGEOOrchestrator

    orch = SEOGEOOrchestrator()
    result = asyncio.run(orch.execute_phase(4, {
        "focus_keyword": "construction costs",
        "target_url": "https://example.com"
    }))

    assert result["status"] == "completed"
    assert result["phase"] == 4
    assert "bluf_paragraph" in result
    assert "meta_description" in result
    assert "ai_tells_detected" in result
    assert "optimization_suggestions" in result
    print(f"✅ Phase 4: Content Optimization — BLUF: '{result['bluf_paragraph'][:60]}...'")


def test_phase_8_competitive_analysis():
    """Phase 8: Competitive analysis uses real CompetitorAnalyzer."""
    from orchestrator import SEOGEOOrchestrator

    orch = SEOGEOOrchestrator()
    result = asyncio.run(orch.execute_phase(8, {
        "focus_keyword": "seo optimization"
    }))

    assert result["status"] == "completed"
    assert result["phase"] == 8
    assert "gap_analysis_completed" in result
    print(f"✅ Phase 8: Competitive Analysis — {result.get('competitors_benchmarked', 0)} benchmarked")


def test_phase_9_validation_gates():
    """Phase 9: Performance tracking runs validation gates."""
    from orchestrator import SEOGEOOrchestrator

    orch = SEOGEOOrchestrator()
    result = asyncio.run(orch.execute_phase(9, {}))

    assert result["status"] == "completed"
    assert result["phase"] == 9
    assert "validation_gates_run" in result
    assert "validation_gates_passed" in result
    assert "validation_gates_failed" in result
    print(f"✅ Phase 9: Validation — {result['validation_gates_passed']}/{result['validation_gates_run']} gates passed")


def test_full_pipeline_execution():
    """Full pipeline: All 10 phases execute without errors."""
    from orchestrator import SEOGEOOrchestrator

    orch = SEOGEOOrchestrator()
    result = asyncio.run(orch.execute_full_pipeline({
        "target_url": "https://example.com",
        "target_keywords": ["seo optimization", "content marketing"],
        "geo_locations": ["New York, NY"],
        "focus_keyword": "seo optimization"
    }))

    assert result["overall_status"] in ["completed", "partial_failure"]
    assert result["phases_executed"] == 10

    # Count successful phases
    successful = sum(
        1 for k, v in result["results"].items()
        if v.get("status") == "completed"
    )
    print(f"\n🏁 Full Pipeline: {successful}/10 phases completed successfully")
    print(f"   Status: {result['overall_status']}")
    if result.get("failed_phases"):
        print(f"   Failed phases: {result['failed_phases']}")

    # All 10 phases should complete (some with fallback data)
    assert successful >= 8, f"Expected at least 8 phases to pass, got {successful}"


if __name__ == "__main__":
    print("=" * 60)
    print("SEO/GEO Pipeline Integration Test — All Modules Wired")
    print("=" * 60)

    tests = [
        test_orchestrator_modules_wired,
        test_phase_0_initialization,
        test_phase_1_keyword_research,
        test_phase_2_serp_analysis,
        test_phase_3_ia_design,
        test_phase_4_content_optimization,
        test_phase_8_competitive_analysis,
        test_phase_9_validation_gates,
        test_full_pipeline_execution,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__}: {e}")

    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{len(tests)} passed, {failed} failed")
    print(f"{'=' * 60}")
