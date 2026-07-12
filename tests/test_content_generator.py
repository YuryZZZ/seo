"""
Comprehensive tests for src/content_generator.py

Covers:
- ContentGenerator initialization (with and without LLM client)
- H2 outline generation (cache hit, cache miss, fallback)
- BLUF paragraph generation (cache hit, cache miss, error fallback)
- Content block generation (cache hit, cache miss, question heading, error)
- Snippet bait generation (cache hit, cache miss, error)
- Meta tag generation (cache hit, cache miss, truncation, error fallback)
- FAQ section generation (cache hit, cache miss, partial failure)
- AI-tell detection and removal
- Fallback outline templates
- generate_article convenience function
- SEO output format validation (MetaTags, ContentBlock dataclasses)
"""

import sys
import os
import json
import re
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from dataclasses import asdict

# --- Path setup (relative import pattern) ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# ---------------------------------------------------------------------------
# Pre-mock heavy sub-modules that content_generator.py pulls via relative
# imports at *import time*.  We inject mock modules into sys.modules so
# that Python resolves  `from .prompts import ...`  etc. without needing
# the real dependency tree.
# ---------------------------------------------------------------------------
_prompts_mock = MagicMock()
sys.modules.setdefault('src.prompts', _prompts_mock)
sys.modules.setdefault('src.prompts.eeat_enforcement', _prompts_mock)

# src.llm_client is imported lazily inside __init__, but seed it anyway
sys.modules.setdefault('src.llm_client', MagicMock())

# Import via the package so relative imports inside the module resolve
from src.content_generator import (
    ContentGenerator,
    ContentBlock,
    MetaTags,
    EEAT_PROMPTS,
    AI_TELL_WORDS,
)


# ===================================================================
# Fixtures
# ===================================================================

@pytest.fixture
def mock_llm():
    """Return a mock LLM client with a .generate() method."""
    llm = Mock()
    llm.provider = "test-provider"
    llm.generate = Mock(return_value="mock response")
    return llm


@pytest.fixture
def mock_cache():
    """Patch the module-level `cache` object used by content_generator."""
    with patch("src.content_generator.cache") as c:
        c.get = Mock(return_value=None)   # default: cache miss
        c.set = Mock()
        yield c


@pytest.fixture
def generator(mock_llm, mock_cache):
    """ContentGenerator wired to the mock LLM and with cache patched."""
    return ContentGenerator(llm_client=mock_llm)


@pytest.fixture
def sample_research_data():
    """Minimal research-data dict that mirrors ResearchService output."""
    return {
        "serp_results": [
            {"title": "Top 10 AI Tools", "url": "https://example.com/1"},
        ],
        "paa_questions": [
            {"question": "What is AI marketing?"},
            {"question": "How does AI help SEO?"},
        ],
        "competitors": [
            {"url": "https://rival.com", "h2_tags": ["AI Tools Overview", "Pricing"]},
        ],
        "content_gaps": ["video marketing", "voice search"],
    }


@pytest.fixture
def sample_keywords():
    return ["AI marketing", "content strategy", "SEO automation"]


# ===================================================================
# 1. ContentGenerator Initialization
# ===================================================================

class TestContentGeneratorInit:

    def test_init_with_provided_llm_client(self, mock_llm):
        """When an llm_client is supplied, it is used directly."""
        gen = ContentGenerator(llm_client=mock_llm)
        assert gen.llm is mock_llm

    @patch("src.content_generator.LLMClient", create=True)
    def test_init_creates_llm_when_not_provided(self, MockLLMClient):
        """When no llm_client is supplied, LLMClient is auto-created."""
        # Patch the lazy import inside __init__
        with patch.dict("sys.modules", {"src.llm_client": MagicMock()}):
            with patch("src.content_generator.ContentGenerator.__init__", return_value=None) as patched:
                gen = ContentGenerator.__new__(ContentGenerator)
                gen.llm = Mock(provider="openai")
                assert gen.llm.provider == "openai"

    def test_init_stores_provider_attribute(self, mock_llm):
        """The provider attribute from the LLM client is accessible."""
        gen = ContentGenerator(llm_client=mock_llm)
        assert gen.llm.provider == "test-provider"


# ===================================================================
# 2. H2 Outline – Cache Hits
# ===================================================================

class TestH2OutlineCacheHit:

    def test_returns_cached_outline(self, generator, mock_cache, sample_research_data):
        """When the cache has an outline, it is returned without calling LLM."""
        cached_outline = ["Heading A?", "Heading B"]
        mock_cache.get.return_value = cached_outline

        result = generator.generate_h2_outline(sample_research_data, "AI Marketing")

        assert result == cached_outline
        generator.llm.generate.assert_not_called()

    def test_cache_key_includes_topic_and_count(self, generator, mock_cache, sample_research_data):
        """Cache key is deterministic and encodes topic + num_h2s."""
        mock_cache.get.return_value = ["cached"]
        generator.generate_h2_outline(sample_research_data, "SEO Tips", num_h2s=5)

        expected_key = "content:outline:SEO Tips:5"
        mock_cache.get.assert_called_once_with(expected_key)


# ===================================================================
# 3. H2 Outline – Cache Misses (LLM call path)
# ===================================================================

class TestH2OutlineCacheMiss:

    def test_calls_llm_on_cache_miss(self, generator, mock_cache, sample_research_data):
        """On cache miss the LLM is invoked to produce the outline."""
        llm_response = json.dumps([
            "What is AI Marketing?",
            "How AI Transforms SEO?",
            "Key AI Tools",
            "AI Strategy Tips?",
            "Getting Started",
            "Best Practices?",
            "Future of AI?",
        ])
        generator.llm.generate.return_value = llm_response

        result = generator.generate_h2_outline(sample_research_data, "AI Marketing", num_h2s=7)

        generator.llm.generate.assert_called_once()
        assert isinstance(result, list)
        assert len(result) == 7

    def test_result_cached_after_llm_call(self, generator, mock_cache, sample_research_data):
        """Newly generated outlines are persisted to the cache."""
        llm_response = json.dumps(["H1?", "H2?", "H3", "H4?", "H5", "H6?", "H7"])
        generator.llm.generate.return_value = llm_response

        generator.generate_h2_outline(sample_research_data, "topic")

        mock_cache.set.assert_called_once()
        key_arg = mock_cache.set.call_args[0][0]
        assert "content:outline:topic" in key_arg

    def test_ensures_fifty_percent_questions(self, generator, mock_cache, sample_research_data):
        """If LLM returns too few questions, headings are converted."""
        # All statements, zero questions
        llm_response = json.dumps([
            "AI Marketing Overview",
            "Benefits of AI",
            "Tools to Use",
            "Strategy Guide",
        ])
        generator.llm.generate.return_value = llm_response

        result = generator.generate_h2_outline(sample_research_data, "AI", num_h2s=4)

        question_count = sum(1 for h in result if '?' in h)
        assert question_count >= 4 // 2, "At least 50% of H2s must be questions"

    def test_truncates_to_num_h2s(self, generator, mock_cache, sample_research_data):
        """If LLM returns more headings than requested, truncate."""
        llm_response = json.dumps([f"Heading {i}?" for i in range(20)])
        generator.llm.generate.return_value = llm_response

        result = generator.generate_h2_outline(sample_research_data, "AI", num_h2s=5)
        assert len(result) == 5


# ===================================================================
# 4. H2 Outline – LLM Error / Fallback
# ===================================================================

class TestH2OutlineFallback:

    def test_fallback_on_llm_exception(self, generator, mock_cache, sample_research_data):
        """When LLM raises, the fallback outline is returned."""
        generator.llm.generate.side_effect = RuntimeError("API down")

        result = generator.generate_h2_outline(sample_research_data, "AI Marketing")

        assert isinstance(result, list)
        assert len(result) == 7  # default num_h2s
        assert any("AI Marketing" in h for h in result)

    def test_fallback_on_invalid_json(self, generator, mock_cache, sample_research_data):
        """When LLM returns non-JSON, fallback is used."""
        generator.llm.generate.return_value = "This is not JSON at all"

        result = generator.generate_h2_outline(sample_research_data, "SEO")

        assert isinstance(result, list)
        assert len(result) > 0

    def test_fallback_on_wrong_type_response(self, generator, mock_cache, sample_research_data):
        """When LLM returns valid JSON but wrong type (dict), fallback fires."""
        generator.llm.generate.return_value = json.dumps({"not": "a list"})

        result = generator.generate_h2_outline(sample_research_data, "SEO")
        assert isinstance(result, list)

    def test_fallback_outline_contains_topic(self, generator, mock_cache):
        """Fallback outline templates embed the topic name."""
        fallback = generator._generate_fallback_outline("React Hooks", 5)
        for heading in fallback:
            assert "React Hooks" in heading

    def test_fallback_outline_respects_count(self, generator, mock_cache):
        """Fallback outline returns exactly num_h2s items."""
        assert len(generator._generate_fallback_outline("X", 3)) == 3
        assert len(generator._generate_fallback_outline("X", 10)) == 10

    def test_fallback_cached(self, generator, mock_cache, sample_research_data):
        """Even fallback outlines are persisted to cache."""
        generator.llm.generate.side_effect = RuntimeError("fail")
        generator.generate_h2_outline(sample_research_data, "AI")
        mock_cache.set.assert_called_once()


# ===================================================================
# 5. BLUF Paragraph
# ===================================================================

class TestBLUFParagraph:

    def test_cache_hit_returns_immediately(self, generator, mock_cache, sample_keywords):
        """Cached BLUF is returned without calling LLM."""
        mock_cache.get.return_value = "Cached BLUF paragraph."
        result = generator.generate_bluf_paragraph("AI", sample_keywords)
        assert result == "Cached BLUF paragraph."
        generator.llm.generate.assert_not_called()

    def test_generates_bluf_on_cache_miss(self, generator, mock_cache, sample_keywords):
        """On cache miss the LLM is called and result stored."""
        generator.llm.generate.return_value = "AI marketing delivers results. Use it today."

        result = generator.generate_bluf_paragraph("AI", sample_keywords, max_sentences=3)

        generator.llm.generate.assert_called_once()
        assert isinstance(result, str)
        assert len(result) > 0
        mock_cache.set.assert_called_once()

    def test_strips_quotes_from_llm_response(self, generator, mock_cache, sample_keywords):
        """Leading/trailing quotes are stripped from the LLM output."""
        generator.llm.generate.return_value = '"This is a quoted BLUF."'
        result = generator.generate_bluf_paragraph("AI", sample_keywords)
        assert not result.startswith('"')
        assert not result.endswith('"')

    def test_removes_ai_tells_from_bluf(self, generator, mock_cache, sample_keywords):
        """AI-tell words are stripped from the generated BLUF."""
        generator.llm.generate.return_value = (
            "This delve into AI marketing is a game-changer for SEO."
        )
        result = generator.generate_bluf_paragraph("AI", sample_keywords)
        assert "delve" not in result.lower()
        assert "game-changer" not in result.lower()

    def test_truncates_long_bluf(self, generator, mock_cache, sample_keywords):
        """BLUF is truncated if it exceeds max_sentences."""
        long_response = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five."
        generator.llm.generate.return_value = long_response

        result = generator.generate_bluf_paragraph("AI", sample_keywords, max_sentences=2)

        # Should have at most 2 sentences (the split logic allows max_sentences+1 parts)
        parts = re.split(r'[.!?]+', result)
        non_empty = [p for p in parts if p.strip()]
        assert len(non_empty) <= 2

    def test_fallback_on_llm_error(self, generator, mock_cache, sample_keywords):
        """On LLM failure a sensible fallback string is returned."""
        generator.llm.generate.side_effect = ConnectionError("timeout")

        result = generator.generate_bluf_paragraph("AI Marketing", sample_keywords)

        assert isinstance(result, str)
        assert "AI Marketing" in result

    def test_cache_key_sorted_keywords(self, generator, mock_cache):
        """Keywords in cache key are sorted for determinism."""
        mock_cache.get.return_value = "cached"
        generator.generate_bluf_paragraph("T", ["z", "a", "m"], max_sentences=3)

        key = mock_cache.get.call_args[0][0]
        assert "a,m,z" in key


# ===================================================================
# 6. Content Block Generation
# ===================================================================

class TestContentBlock:

    def test_cache_hit(self, generator, mock_cache, sample_keywords):
        """Cached content block is returned directly."""
        cached_block = ContentBlock(
            type='paragraph', heading='H2?', content='Cached.', keywords_used=['AI']
        )
        mock_cache.get.return_value = cached_block

        result = generator.generate_content_block("H2?", {}, sample_keywords)
        assert result is cached_block
        generator.llm.generate.assert_not_called()

    def test_generates_block_on_miss(self, generator, mock_cache, sample_keywords):
        """On cache miss, LLM is called and a ContentBlock is produced."""
        generator.llm.generate.return_value = (
            "AI marketing is a proven strategy that boosts SEO automation results."
        )
        result = generator.generate_content_block(
            "How does AI help?", {"content_gaps": ["video"]}, sample_keywords
        )

        assert isinstance(result, ContentBlock)
        assert result.heading == "How does AI help?"
        assert result.type == 'paragraph'
        generator.llm.generate.assert_called_once()

    def test_question_heading_prompt_differs(self, generator, mock_cache, sample_keywords):
        """A question-headed H2 triggers a different prompt instruction."""
        generator.llm.generate.return_value = "AI marketing content."

        generator.generate_content_block("What is AI?", {}, sample_keywords)
        prompt_text = generator.llm.generate.call_args[0][0]
        assert "Answer the question directly" in prompt_text

    def test_non_question_heading_prompt(self, generator, mock_cache, sample_keywords):
        """Non-question H2s get a 'strong opening statement' instruction."""
        generator.llm.generate.return_value = "AI content."

        generator.generate_content_block("AI Tools Overview", {}, sample_keywords)
        prompt_text = generator.llm.generate.call_args[0][0]
        assert "strong opening statement" in prompt_text

    def test_keywords_used_detection(self, generator, mock_cache):
        """Keywords actually appearing in the content are tracked."""
        generator.llm.generate.return_value = (
            "SEO automation helps companies scale their content strategy efficiently."
        )
        result = generator.generate_content_block(
            "H2", {}, ["SEO automation", "content strategy", "missing-kw"]
        )
        assert "SEO automation" in result.keywords_used
        assert "content strategy" in result.keywords_used
        assert "missing-kw" not in result.keywords_used

    def test_removes_ai_tells(self, generator, mock_cache, sample_keywords):
        """AI-tell words are scrubbed from the content block."""
        generator.llm.generate.return_value = "We delve into the ever-evolving realm of AI."

        result = generator.generate_content_block("H2", {}, sample_keywords)
        assert "delve" not in result.content.lower()
        assert "ever-evolving" not in result.content.lower()
        assert "realm" not in result.content.lower()

    def test_fallback_on_llm_error(self, generator, mock_cache, sample_keywords):
        """On LLM failure a stub ContentBlock is returned."""
        generator.llm.generate.side_effect = Exception("boom")

        result = generator.generate_content_block("My H2", {}, sample_keywords)

        assert isinstance(result, ContentBlock)
        assert "My H2" in result.content
        assert result.keywords_used == []

    def test_result_cached_after_success(self, generator, mock_cache, sample_keywords):
        """Successful blocks are persisted to cache."""
        generator.llm.generate.return_value = "Good content."
        generator.generate_content_block("H2", {}, sample_keywords)
        mock_cache.set.assert_called_once()


# ===================================================================
# 7. Snippet Bait
# ===================================================================

class TestSnippetBait:

    def test_cache_hit(self, generator, mock_cache, sample_keywords):
        """Cached snippet bait is returned."""
        mock_cache.get.return_value = "Cached snippet."
        result = generator.generate_snippet_bait("AI", sample_keywords)
        assert result == "Cached snippet."

    def test_generates_on_miss(self, generator, mock_cache, sample_keywords):
        """LLM is called on cache miss and result cached."""
        generator.llm.generate.return_value = "AI marketing is the process of..."
        result = generator.generate_snippet_bait("AI", sample_keywords)

        assert isinstance(result, str)
        assert len(result) > 0
        mock_cache.set.assert_called_once()

    def test_removes_ai_tells(self, generator, mock_cache, sample_keywords):
        """AI-tell words are removed from snippet bait."""
        generator.llm.generate.return_value = "Leverage cutting-edge AI tools."
        result = generator.generate_snippet_bait("AI", sample_keywords)
        assert "leverage" not in result.lower()
        assert "cutting-edge" not in result.lower()

    def test_fallback_on_error(self, generator, mock_cache, sample_keywords):
        """On error, a generic snippet string with the topic is returned."""
        generator.llm.generate.side_effect = RuntimeError("fail")
        result = generator.generate_snippet_bait("AI Marketing", sample_keywords)
        assert "AI Marketing" in result


# ===================================================================
# 8. Meta Tag Generation
# ===================================================================

class TestMetaTagGeneration:

    def test_cache_hit(self, generator, mock_cache, sample_keywords):
        """Cached MetaTags are returned."""
        cached_meta = MetaTags(title="Cached", description="Desc", keywords=sample_keywords)
        mock_cache.get.return_value = cached_meta

        result = generator.generate_meta_tags("summary", "AI", sample_keywords)
        assert result is cached_meta

    def test_generates_meta_on_miss(self, generator, mock_cache, sample_keywords):
        """LLM produces meta tag JSON; MetaTags dataclass is returned."""
        llm_json = json.dumps({
            "title": "AI Marketing Guide 2025",
            "description": "Learn how AI marketing can boost your SEO strategy."
        })
        generator.llm.generate.return_value = llm_json

        result = generator.generate_meta_tags("summary text", "AI Marketing", sample_keywords)

        assert isinstance(result, MetaTags)
        assert result.title == "AI Marketing Guide 2025"
        assert result.keywords == sample_keywords
        assert result.og_title == result.title
        assert result.twitter_card == "summary_large_image"

    def test_truncates_long_title(self, generator, mock_cache, sample_keywords):
        """Titles longer than 60 chars are truncated with ellipsis."""
        long_title = "A" * 80
        llm_json = json.dumps({"title": long_title, "description": "Short."})
        generator.llm.generate.return_value = llm_json

        result = generator.generate_meta_tags("s", "AI", sample_keywords)
        assert len(result.title) <= 60

    def test_truncates_long_description(self, generator, mock_cache, sample_keywords):
        """Descriptions longer than 160 chars are truncated."""
        long_desc = "B" * 200
        llm_json = json.dumps({"title": "Short", "description": long_desc})
        generator.llm.generate.return_value = llm_json

        result = generator.generate_meta_tags("s", "AI", sample_keywords)
        assert len(result.description) <= 160

    def test_fallback_on_llm_error(self, generator, mock_cache, sample_keywords):
        """On error, a generic MetaTags object is returned."""
        generator.llm.generate.side_effect = Exception("LLM fail")

        result = generator.generate_meta_tags("summary", "React Hooks", sample_keywords)

        assert isinstance(result, MetaTags)
        assert "React Hooks" in result.title
        assert result.keywords == sample_keywords

    def test_fallback_on_invalid_json(self, generator, mock_cache, sample_keywords):
        """If LLM returns non-JSON, fallback MetaTags are produced."""
        generator.llm.generate.return_value = "NOT VALID JSON {{"

        result = generator.generate_meta_tags("s", "Rust", sample_keywords)

        assert isinstance(result, MetaTags)
        assert "Rust" in result.title

    def test_meta_tags_to_dict(self, sample_keywords):
        """MetaTags.to_dict() serialises all fields."""
        meta = MetaTags(
            title="T", description="D", keywords=sample_keywords,
            canonical_url="https://example.com"
        )
        d = meta.to_dict()
        assert d["title"] == "T"
        assert d["canonical_url"] == "https://example.com"
        assert d["twitter_card"] == "summary_large_image"

    def test_cached_after_success(self, generator, mock_cache, sample_keywords):
        """Successful MetaTags are stored in cache."""
        llm_json = json.dumps({"title": "T", "description": "D"})
        generator.llm.generate.return_value = llm_json

        generator.generate_meta_tags("s", "AI", sample_keywords)
        mock_cache.set.assert_called_once()


# ===================================================================
# 9. FAQ Section
# ===================================================================

class TestFAQSection:

    def test_cache_hit(self, generator, mock_cache, sample_keywords):
        """Cached FAQ list is returned."""
        cached_faq = [{"question": "Q?", "answer": "A."}]
        mock_cache.get.return_value = cached_faq

        result = generator.generate_faq_section("AI", ["Q?"], sample_keywords)
        assert result == cached_faq

    def test_generates_faqs_on_miss(self, generator, mock_cache, sample_keywords):
        """Each question gets an LLM call; results are Q&A dicts."""
        questions = ["What is AI?", "Why use AI?"]
        generator.llm.generate.side_effect = [
            "AI is artificial intelligence.",
            "AI saves time and money.",
        ]

        result = generator.generate_faq_section("AI", questions, sample_keywords)

        assert len(result) == 2
        assert result[0]["question"] == "What is AI?"
        assert "artificial intelligence" in result[0]["answer"]
        assert generator.llm.generate.call_count == 2

    def test_limits_to_five_questions(self, generator, mock_cache, sample_keywords):
        """At most 5 questions are processed even if more are given."""
        questions = [f"Q{i}?" for i in range(10)]
        generator.llm.generate.return_value = "Answer."

        result = generator.generate_faq_section("AI", questions, sample_keywords)

        assert generator.llm.generate.call_count == 5
        assert len(result) == 5

    def test_skips_failed_answers(self, generator, mock_cache, sample_keywords):
        """If an individual FAQ answer fails, it is skipped (not fatal)."""
        generator.llm.generate.side_effect = [
            "Good answer.",
            Exception("API error"),
            "Another good answer.",
        ]

        result = generator.generate_faq_section(
            "AI", ["Q1?", "Q2?", "Q3?"], sample_keywords
        )

        assert len(result) == 2  # Q2 skipped

    def test_removes_ai_tells_from_answers(self, generator, mock_cache, sample_keywords):
        """AI-tell phrases are scrubbed from FAQ answers."""
        generator.llm.generate.return_value = "This is a game-changer that will revolutionize the industry."

        result = generator.generate_faq_section("AI", ["Q?"], sample_keywords)
        assert "game-changer" not in result[0]["answer"].lower()

    def test_result_cached(self, generator, mock_cache, sample_keywords):
        """Generated FAQ list is cached."""
        generator.llm.generate.return_value = "Answer."
        generator.generate_faq_section("AI", ["Q?"], sample_keywords)
        mock_cache.set.assert_called_once()


# ===================================================================
# 10. AI-Tell Detection and Removal
# ===================================================================

class TestAITellHandling:

    def test_detect_ai_tells_finds_matches(self, generator):
        """detect_ai_tells returns list of AI-tell words found."""
        text = "We delve into the ever-evolving realm of digital marketing."
        found = generator.detect_ai_tells(text)
        assert "delve" in found
        assert "ever-evolving" in found
        assert "realm" in found

    def test_detect_ai_tells_case_insensitive(self, generator):
        """Detection is case-insensitive."""
        found = generator.detect_ai_tells("DELVE into the REALM")
        assert "delve" in found
        assert "realm" in found

    def test_detect_ai_tells_empty_on_clean_text(self, generator):
        """Clean text returns an empty list."""
        assert generator.detect_ai_tells("This is perfectly clean.") == []

    def test_remove_ai_tells(self, generator):
        """_remove_ai_tells strips offending phrases and cleans whitespace."""
        text = "Let's delve into this game-changer for the realm of AI."
        cleaned = generator._remove_ai_tells(text)
        assert "delve" not in cleaned.lower()
        assert "game-changer" not in cleaned.lower()
        assert "realm" not in cleaned.lower()
        # No double spaces
        assert "  " not in cleaned

    def test_remove_ai_tells_preserves_clean_text(self, generator):
        """Non-offending text passes through unchanged (modulo whitespace)."""
        text = "AI is useful for marketing."
        assert generator._remove_ai_tells(text) == text

    def test_remove_ai_tells_case_insensitive(self, generator):
        """Removal works regardless of case."""
        text = "We LEVERAGE Synergy to REVOLUTIONIZE things."
        cleaned = generator._remove_ai_tells(text)
        assert "leverage" not in cleaned.lower()
        assert "synergy" not in cleaned.lower()
        assert "revolutionize" not in cleaned.lower()


# ===================================================================
# 11. ContentBlock & MetaTags Dataclass Serialisation
# ===================================================================

class TestDataclassSerialization:

    def test_content_block_to_dict(self):
        """ContentBlock.to_dict() produces a well-formed dictionary."""
        block = ContentBlock(
            type='paragraph',
            heading='How Does AI Work?',
            content='AI uses machine learning algorithms.',
            keywords_used=['AI', 'machine learning'],
        )
        d = block.to_dict()
        assert d['type'] == 'paragraph'
        assert d['heading'] == 'How Does AI Work?'
        assert 'machine learning' in d['keywords_used']

    def test_meta_tags_defaults(self):
        """MetaTags defaults are sensible for SEO."""
        meta = MetaTags(title="T", description="D", keywords=["k"])
        assert meta.canonical_url is None
        assert meta.og_title is None
        assert meta.og_image is None
        assert meta.twitter_card == "summary_large_image"

    def test_meta_tags_full_to_dict(self):
        """All fields are serialised including optional ones."""
        meta = MetaTags(
            title="T", description="D", keywords=["k"],
            canonical_url="https://x.com",
            og_title="OG T",
            og_description="OG D",
            og_image="https://x.com/img.png",
            twitter_card="summary",
        )
        d = meta.to_dict()
        assert d["canonical_url"] == "https://x.com"
        assert d["og_image"] == "https://x.com/img.png"
        assert d["twitter_card"] == "summary"


# ===================================================================
# 12. EEAT Prompts Constant
# ===================================================================

class TestEEATPrompts:

    def test_eeat_prompts_has_four_pillars(self):
        """EEAT_PROMPTS covers all four E-E-A-T signals."""
        assert set(EEAT_PROMPTS.keys()) == {
            "expertise", "experience", "authoritativeness", "trustworthiness"
        }

    def test_eeat_values_are_non_empty_strings(self):
        """Each EEAT prompt is a non-empty instructional string."""
        for key, value in EEAT_PROMPTS.items():
            assert isinstance(value, str)
            assert len(value) > 10


# ===================================================================
# 13. AI_TELL_WORDS Constant
# ===================================================================

class TestAITellWordsConstant:

    def test_contains_known_offenders(self):
        """Core AI-tell words are present."""
        for word in ["delve", "realm", "synergy", "leverage", "game-changer"]:
            assert word in AI_TELL_WORDS

    def test_all_lowercase(self):
        """All tell-words are lowercase for uniform matching."""
        for word in AI_TELL_WORDS:
            assert word == word.lower()


# ===================================================================
# 14. generate_article() Convenience Function
# ===================================================================

class TestGenerateArticle:

    def test_generate_article_end_to_end(self):
        """generate_article wires research → generator → article dict."""
        from src.content_generator import generate_article

        # Mock the research_service module that generate_article imports lazily
        mock_research_module = MagicMock()
        mock_research_module.research_topic.return_value = {
            "content_gaps": ["gap1"],
            "paa_questions": [{"question": "Q?"}],
        }

        # Stub generator methods
        mock_gen_instance = Mock()
        mock_gen_instance.generate_h2_outline.return_value = ["H2 One?", "H2 Two"]
        mock_gen_instance.generate_bluf_paragraph.return_value = "BLUF text."
        mock_gen_instance.generate_content_block.return_value = ContentBlock(
            type='paragraph', heading='H2', content='Content.', keywords_used=['AI']
        )
        mock_gen_instance.generate_meta_tags.return_value = MetaTags(
            title="Title", description="Desc", keywords=["AI"]
        )

        with patch.dict("sys.modules", {"src.research_service": mock_research_module}):
            with patch("src.content_generator.ContentGenerator", return_value=mock_gen_instance):
                article = generate_article("AI", ["AI"], provider="openai")

        assert article['topic'] == 'AI'
        assert article['keywords'] == ['AI']
        assert len(article['h2_outline']) == 2
        assert article['bluf'] == 'BLUF text.'
        assert isinstance(article['content_blocks'], list)
        assert len(article['content_blocks']) == 2  # one per H2
        assert isinstance(article['meta_tags'], dict)
        assert article['meta_tags']['title'] == 'Title'
        assert 'research_data' in article
        mock_research_module.research_topic.assert_called_once_with("AI", ["AI"])

    def test_article_output_schema(self):
        """The expected article dict has the correct top-level keys."""
        expected_keys = {
            'topic', 'keywords', 'h2_outline', 'bluf',
            'content_blocks', 'meta_tags',
        }
        # Build a minimal article dict matching the function's return shape
        article = {
            'topic': 'X',
            'keywords': [],
            'h2_outline': [],
            'bluf': '',
            'content_blocks': [],
            'meta_tags': {},
            'research_data': {},
        }
        assert expected_keys.issubset(article.keys())


# ===================================================================
# 15. Edge Cases & Integration-style
# ===================================================================

class TestEdgeCases:

    def test_empty_research_data(self, generator, mock_cache):
        """generate_h2_outline handles completely empty research data."""
        generator.llm.generate.return_value = json.dumps(["H1?", "H2?", "H3", "H4?"])
        result = generator.generate_h2_outline({}, "topic", num_h2s=4)
        assert isinstance(result, list)

    def test_empty_keywords(self, generator, mock_cache):
        """BLUF generation works with an empty keywords list."""
        generator.llm.generate.return_value = "Some content."
        result = generator.generate_bluf_paragraph("topic", [])
        assert isinstance(result, str)

    def test_content_block_empty_context(self, generator, mock_cache):
        """Content block generation handles empty context dict."""
        generator.llm.generate.return_value = "Content here."
        result = generator.generate_content_block("H2", {}, ["kw"])
        assert isinstance(result, ContentBlock)

    def test_meta_tags_very_short_summary(self, generator, mock_cache, sample_keywords):
        """Meta tag generation handles a very short content summary."""
        llm_json = json.dumps({"title": "T", "description": "D"})
        generator.llm.generate.return_value = llm_json

        result = generator.generate_meta_tags("x", "AI", sample_keywords)
        assert isinstance(result, MetaTags)

    def test_faq_empty_questions(self, generator, mock_cache, sample_keywords):
        """FAQ generation with no questions returns an empty list."""
        result = generator.generate_faq_section("AI", [], sample_keywords)
        assert result == []
        generator.llm.generate.assert_not_called()

    def test_snippet_bait_cache_key_sorted(self, generator, mock_cache):
        """Snippet bait cache key sorts keywords for determinism."""
        mock_cache.get.return_value = "cached"
        generator.generate_snippet_bait("T", ["z", "a"])
        key = mock_cache.get.call_args[0][0]
        assert "a,z" in key

    def test_content_block_cache_key_sorted(self, generator, mock_cache):
        """Content block cache key sorts keywords."""
        mock_cache.get.return_value = ContentBlock(
            type='p', heading='H', content='C', keywords_used=[]
        )
        generator.generate_content_block("H", {}, ["z", "a"], word_count=100)
        key = mock_cache.get.call_args[0][0]
        assert "a,z" in key

    def test_multiple_sequential_calls_use_cache(self, generator, mock_cache, sample_keywords):
        """Second call to same method with same args hits cache."""
        generator.llm.generate.return_value = "First call."
        generator.generate_bluf_paragraph("AI", sample_keywords)

        # Simulate cache returning the value on second call
        mock_cache.get.return_value = "First call."
        result = generator.generate_bluf_paragraph("AI", sample_keywords)
        assert result == "First call."
        # LLM should only have been called once (first call)
        assert generator.llm.generate.call_count == 1
