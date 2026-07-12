"""Tests for ContentFreshnessAnalyzer — age analysis, freshness scoring, update suggestions."""

import sys
import os
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import pytest
from content_freshness import ContentFreshnessAnalyzer


@pytest.fixture
def analyzer():
    return ContentFreshnessAnalyzer()


class TestAnalyzeContentAge:
    """Test content age analysis."""

    def test_no_years_returns_evergreen(self, analyzer):
        result = analyzer.analyze_content_age("This has no year references.")
        assert result["status"] == "evergreen_or_undated"
        assert result["latest_year_mentioned"] is None

    def test_current_year_is_fresh(self, analyzer):
        text = f"Updated for {analyzer.current_year} season."
        result = analyzer.analyze_content_age(text)
        assert result["status"] == "fresh"
        assert result["latest_year_mentioned"] == analyzer.current_year

    def test_old_year_is_stale(self, analyzer):
        text = "This was written in 2020 and never updated."
        result = analyzer.analyze_content_age(text)
        assert result["status"] == "stale"
        assert result["apparent_age_years"] >= 3

    def test_recent_year_is_aging(self, analyzer):
        recent_year = analyzer.current_year - 1
        text = f"Published in {recent_year}."
        result = analyzer.analyze_content_age(text)
        assert result["status"] == "aging"

    def test_multiple_years_uses_latest(self, analyzer):
        text = f"Founded in 2015, expanded in 2020, updated {analyzer.current_year}."
        result = analyzer.analyze_content_age(text)
        assert result["latest_year_mentioned"] == analyzer.current_year
        assert result["status"] == "fresh"
        assert len(result["all_years_mentioned"]) == 3


class TestCheckFreshnessSignals:
    """Test freshness signal detection."""

    def test_has_current_year(self, analyzer):
        text = f"Best SEO practices {analyzer.current_year}."
        signals = analyzer.check_freshness_signals(text)
        assert signals["has_current_year"] is True

    def test_no_current_year(self, analyzer):
        signals = analyzer.check_freshness_signals("Generic evergreen content.")
        assert signals["has_current_year"] is False

    def test_temporal_words_counted(self, analyzer):
        text = "Recently updated and currently the latest approach."
        signals = analyzer.check_freshness_signals(text)
        assert signals["temporal_words"] >= 3

    def test_outdated_words_counted(self, analyzer):
        text = "Formerly known as something else, in the past it was different."
        signals = analyzer.check_freshness_signals(text)
        assert signals["outdated_words"] >= 2


class TestIdentifyOutdatedContent:
    """Test outdated content identification."""

    def test_flags_old_dates(self, analyzer):
        old_year = analyzer.current_year - 3
        text = f"According to a {old_year} study, results show improvement."
        outdated = analyzer.identify_outdated_content(text)
        assert len(outdated) >= 1

    def test_no_outdated_for_fresh(self, analyzer):
        text = f"In {analyzer.current_year}, this approach is recommended."
        outdated = analyzer.identify_outdated_content(text)
        assert len(outdated) == 0

    def test_empty_text(self, analyzer):
        assert analyzer.identify_outdated_content("") == []


class TestCalculateFreshnessScore:
    """Test freshness scoring (0-100)."""

    def test_max_score_for_fresh_content(self, analyzer):
        text = f"Recently updated for {analyzer.current_year}. Latest techniques."
        score = analyzer.calculate_freshness_score(text)
        assert score >= 70  # Should be high

    def test_low_score_for_stale_content(self, analyzer):
        text = "Written in 2018 about old techniques formerly used."
        score = analyzer.calculate_freshness_score(text)
        assert score < 70  # Should be penalized

    def test_score_bounded_0_to_100(self, analyzer):
        # Even with extremely stale content
        text = "1990 data. Formerly used. In the past. Years ago. Previously."
        score = analyzer.calculate_freshness_score(text)
        assert 0 <= score <= 100

    def test_score_is_integer(self, analyzer):
        score = analyzer.calculate_freshness_score("Some content.")
        assert isinstance(score, int)


class TestSuggestUpdates:
    """Test update suggestions."""

    def test_suggests_adding_current_year(self, analyzer):
        text = "A guide to SEO best practices."
        suggestions = analyzer.suggest_updates(text)
        # Should suggest adding current year
        assert any(str(analyzer.current_year) in s for s in suggestions)

    def test_suggests_topic_section(self, analyzer):
        text = "General content."
        suggestions = analyzer.suggest_updates(text, topic="SEO")
        assert any("SEO" in s for s in suggestions)

    def test_empty_text_returns_suggestions(self, analyzer):
        suggestions = analyzer.suggest_updates("")
        assert isinstance(suggestions, list)


class TestTrackContentDecay:
    """Test content decay tracking."""

    def test_returns_tracking_payload(self, analyzer):
        result = analyzer.track_content_decay("/blog/seo-guide")
        assert result["url"] == "/blog/seo-guide"
        assert result["decay_status"] == "monitoring"
        assert "metrics_to_track" in result

    def test_has_recommendation(self, analyzer):
        result = analyzer.track_content_decay("/any-page")
        assert "recommendation" in result


class TestSetRefreshSchedule:
    """Test refresh scheduling."""

    def test_auto_schedule_for_stale_content(self, analyzer):
        old_text = "Written in 2018 with outdated information."
        schedule = analyzer.set_refresh_schedule(old_text)
        assert "schedule_interval" in schedule

    def test_auto_schedule_for_fresh_content(self, analyzer):
        text = f"Updated for {analyzer.current_year} with latest data."
        schedule = analyzer.set_refresh_schedule(text)
        assert "schedule_interval" in schedule

    def test_manual_interval(self, analyzer):
        schedule = analyzer.set_refresh_schedule("Content", interval="monthly")
        assert "schedule_interval" in schedule
