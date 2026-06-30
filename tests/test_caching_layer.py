"""Unit and integration tests for the caching layer integration."""

import sys
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.cache import cache
from src.content_generator import ContentGenerator, ContentBlock, MetaTags
from src.keyword_researcher import KeywordResearcher


class TestCachingLayer:
    """Test suite for the imp_cache caching layer integration."""

    @pytest.fixture(autouse=True)
    def setup_cache(self):
        """Clear cache before each test."""
        cache.clear()
        yield
        cache.clear()

    def test_content_generator_h2_outline_caching(self):
        """Test that generate_h2_outline caches its output."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = '["What is AI?", "How to use AI?"]'

        generator = ContentGenerator(llm_client=mock_llm)
        research_data = {"serp_results": [], "paa_questions": [], "competitors": []}

        # First call - should invoke LLM
        outline1 = generator.generate_h2_outline(research_data, "caching_test", num_h2s=2)
        assert len(outline1) == 2
        assert mock_llm.generate.call_count == 1

        # Second call - should HIT cache and NOT invoke LLM
        outline2 = generator.generate_h2_outline(research_data, "caching_test", num_h2s=2)
        assert outline2 == outline1
        assert mock_llm.generate.call_count == 1

    def test_content_generator_bluf_caching(self):
        """Test that generate_bluf_paragraph caches its output."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "This is a cached BLUF paragraph."

        generator = ContentGenerator(llm_client=mock_llm)

        # First call
        bluf1 = generator.generate_bluf_paragraph("caching_bluf", ["cache"], max_sentences=2)
        assert bluf1 == "This is a cached BLUF paragraph."
        assert mock_llm.generate.call_count == 1

        # Second call
        bluf2 = generator.generate_bluf_paragraph("caching_bluf", ["cache"], max_sentences=2)
        assert bluf2 == bluf1
        assert mock_llm.generate.call_count == 1

    def test_content_generator_content_block_caching(self):
        """Test that generate_content_block caches its output."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "This is the section body text."

        generator = ContentGenerator(llm_client=mock_llm)
        context = {"content_gaps": []}

        # First call
        block1 = generator.generate_content_block("H2 Heading", context, ["keyword"], word_count=50)
        assert isinstance(block1, ContentBlock)
        assert block1.content == "This is the section body text."
        assert mock_llm.generate.call_count == 1

        # Second call
        block2 = generator.generate_content_block("H2 Heading", context, ["keyword"], word_count=50)
        assert block2 == block1
        assert mock_llm.generate.call_count == 1

    def test_keyword_researcher_scan_caching(self):
        """Test that KeywordResearcher _scan_repository_terms uses global cache across instances."""
        root_path = Path(__file__).parent.parent
        researcher1 = KeywordResearcher(repo_root=root_path)
        
        # Force scan and record terms
        terms1, inv1 = researcher1._scan_repository_terms(max_repository_terms=5)
        assert inv1["cache_hit"] is False

        # Create a new researcher instance
        researcher2 = KeywordResearcher(repo_root=root_path)

        # Perform scan on second instance, should HIT global cache
        terms2, inv2 = researcher2._scan_repository_terms(max_repository_terms=5)
        assert terms2 == terms1
        assert inv2["cache_hit"] is True

    def test_keyword_researcher_research_keywords_caching(self):
        """Test that KeywordResearcher.research_keywords caches results."""
        root_path = Path(__file__).parent.parent
        researcher = KeywordResearcher(repo_root=root_path)

        # Mock inner method to count actual calls
        original_build = researcher._build_keyword_rows
        researcher._build_keyword_rows = MagicMock(side_effect=original_build)

        # First call
        res1 = researcher.research_keywords("test_keyword", limit=10)
        assert res1["seed_keyword"] == "test_keyword"
        assert researcher._build_keyword_rows.call_count == 1

        # Second call
        res2 = researcher.research_keywords("test_keyword", limit=10)
        assert res2["seed_keyword"] == "test_keyword"
        assert researcher._build_keyword_rows.call_count == 1
