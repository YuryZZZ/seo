"""Tests for content_utils module — word count, reading time, FAQ extraction, canonical URLs, quality scoring."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import pytest
from content_utils import (
    word_count,
    reading_time,
    extract_faq_from_headings,
    suggest_canonical_url,
    estimate_content_quality_score,
    count_questions,
    detect_language,
)


class TestWordCount:
    """Test word counting utility."""

    def test_empty_string(self):
        assert word_count("") == 0

    def test_none_input(self):
        assert word_count(None) == 0

    def test_simple_sentence(self):
        assert word_count("hello world foo bar") == 4

    def test_with_punctuation(self):
        assert word_count("Hello, world! How are you?") == 5


class TestReadingTime:
    """Test reading time estimation."""

    def test_empty(self):
        assert reading_time("") == 0

    def test_short_text(self):
        # 10 words at 200 wpm → 1 minute (ceil)
        text = " ".join(["word"] * 10)
        assert reading_time(text) == 1

    def test_long_text(self):
        # 600 words at 200 wpm → 3 minutes
        text = " ".join(["word"] * 600)
        assert reading_time(text) == 3

    def test_custom_wpm(self):
        text = " ".join(["word"] * 300)
        assert reading_time(text, wpm=100) == 3


class TestCountQuestions:
    """Test question counting."""

    def test_no_questions(self):
        assert count_questions("This is a statement.") == 0

    def test_multiple_questions(self):
        assert count_questions("What? Why? How?") == 3

    def test_empty(self):
        assert count_questions("") == 0


class TestExtractFaqFromHeadings:
    """Test FAQ extraction from HTML headings."""

    def test_empty_html(self):
        assert extract_faq_from_headings("") == []

    def test_no_questions(self):
        html = "<h2>Not a Question</h2><p>Some answer.</p>"
        assert extract_faq_from_headings(html) == []

    def test_extracts_question_h2(self):
        html = '<h2>What is SEO?</h2><p>SEO stands for Search Engine Optimization.</p>'
        result = extract_faq_from_headings(html)
        assert len(result) == 1
        assert result[0]["question"] == "What is SEO?"
        assert "Search Engine Optimization" in result[0]["answer"]

    def test_extracts_multiple_faqs(self):
        html = """
        <h2>What is SEO?</h2><p>Search Engine Optimization.</p>
        <h3>Why does SEO matter?</h3><p>It drives organic traffic.</p>
        """
        result = extract_faq_from_headings(html)
        assert len(result) == 2

    def test_ignores_h1_and_h4(self):
        html = '<h1>What is this?</h1><p>Answer.</p><h4>Why?</h4><p>Because.</p>'
        assert extract_faq_from_headings(html) == []


class TestSuggestCanonicalUrl:
    """Test canonical URL generation."""

    def test_simple_title(self):
        result = suggest_canonical_url("SEO Best Practices for 2025")
        assert result == "/seo-best-practices-for-2025"

    def test_with_base_url(self):
        result = suggest_canonical_url("My Article", base_url="https://example.com")
        assert result == "https://example.com/my-article"

    def test_removes_special_characters(self):
        result = suggest_canonical_url("What's the Best SEO Tool?")
        assert "?" not in result
        assert "'" not in result

    def test_empty_title(self):
        assert suggest_canonical_url("") == "/"
        assert suggest_canonical_url("", base_url="https://x.com") == "https://x.com"

    def test_truncates_long_title(self):
        long_title = "a very long title " * 20
        result = suggest_canonical_url(long_title)
        assert len(result) <= 82  # / + max 80 chars

    def test_strips_trailing_base_url_slash(self):
        result = suggest_canonical_url("test", base_url="https://example.com/")
        assert "example.com//test" not in result


class TestEstimateContentQualityScore:
    """Test content quality scoring."""

    def test_empty_text(self):
        result = estimate_content_quality_score("")
        assert result["overall"] == 0

    def test_returns_dict_with_overall(self):
        result = estimate_content_quality_score("Some text here.")
        assert "overall" in result
        assert "details" in result
        assert isinstance(result["overall"], int)

    def test_higher_score_for_structured_content(self):
        simple = "Just some plain text without structure."
        structured = """
        <h2>Section One?</h2><p>Content here</p>
        <h2>Section Two?</h2><p>More content</p>
        <h3>Subsection</h3><p>Even more content</p>
        <a href="/internal">link</a>
        <a href="https://external.com">ext link</a>
        """ + " word" * 500
        
        simple_score = estimate_content_quality_score(simple)["overall"]
        structured_score = estimate_content_quality_score(structured)["overall"]
        assert structured_score > simple_score

    def test_score_bounded(self):
        # Even with extreme content, score should be 0-100
        big_content = ("<h2>Q?</h2><p>A</p>" * 50) + (" word" * 5000)
        result = estimate_content_quality_score(big_content)
        assert 0 <= result["overall"] <= 100

    def test_details_has_all_fields(self):
        result = estimate_content_quality_score("Some text <h2>Header</h2>")
        details = result["details"]
        expected_keys = {"length_score", "structure_score", "question_score", 
                        "link_score", "word_count", "h2_count", "h3_count",
                        "question_count", "internal_links", "external_links"}
        assert expected_keys.issubset(set(details.keys()))


class TestDetectLanguage:
    """Test language detection."""

    def test_english_default(self):
        assert detect_language("Hello world") == "en"

    def test_empty_string(self):
        assert detect_language("") == "en"
