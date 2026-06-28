"""
Unit tests for RowPayloadTemplate class.
Tests cover: initialization, validation, enrichment, serialization.
Aligned with actual implementation in src/row_payload.py
"""

import pytest
import json
from datetime import datetime
from dataclasses import asdict
from typing import Dict, Any, List, Optional

# Import the module under test
import sys
sys.path.insert(0, 'C:/Users/yuryz/Documents/GitHub/Portals/seo/src')

from row_payload import (
    RowPayloadTemplate,
    PayloadStatus,
    ValidationRule,
    PayloadValidator,
    create_empty_payload,
    create_payload_from_dict,
    RowPayload  # Alias
)


class TestRowPayloadTemplateBasics:
    """Test basic RowPayloadTemplate functionality."""
    
    def test_create_empty_payload(self):
        """Test creating an empty payload with default values."""
        payload = create_empty_payload()
        
        assert payload is not None
        assert payload.post_id is None
        assert payload.post_title == ""
    
    def test_payload_with_required_fields(self):
        """Test creating payload with required fields."""
        payload = RowPayloadTemplate(
            post_id=12345,
            post_title="Test Post Title",
            post_content="Test content for the post."
        )
        
        assert payload.post_id == 12345
        assert payload.post_title == "Test Post Title"
        assert payload.post_content == "Test content for the post."
    
    def test_payload_status_enum(self):
        """Test PayloadStatus enum values."""
        assert PayloadStatus.EMPTY.value == "empty"
        assert PayloadStatus.VALID.value == "valid"
        assert PayloadStatus.INVALID.value == "invalid"
        assert PayloadStatus.PROCESSING.value == "processing"
        assert PayloadStatus.COMPLETED.value == "completed"
        assert PayloadStatus.FAILED.value == "failed"
    
    def test_payload_to_dict(self):
        """Test converting payload to dictionary."""
        payload = RowPayloadTemplate(
            post_id=123,
            post_title="Test",
            seo_title="SEO Test Title"
        )
        
        result = payload.to_dict()
        
        assert isinstance(result, dict)
        assert result["post_id"] == 123
        assert result["post_title"] == "Test"
        assert result["seo_title"] == "SEO Test Title"
    
    def test_payload_to_json(self):
        """Test serializing payload to JSON."""
        payload = RowPayloadTemplate(
            post_id=456,
            post_title="JSON Test",
            meta_description="Test meta description"
        )
        
        json_str = payload.to_json()
        result = json.loads(json_str)
        
        assert result["post_id"] == 456
        assert result["post_title"] == "JSON Test"
    
    def test_create_payload_from_dict(self):
        """Test creating payload from dictionary."""
        data = {
            "post_id": 789,
            "post_title": "Dict Test",
            "focus_keyword": "test keyword"
        }
        
        payload = create_payload_from_dict(data)
        
        assert payload.post_id == 789
        assert payload.post_title == "Dict Test"
        assert payload.focus_keyword == "test keyword"
    
    def test_row_payload_alias(self):
        """Test that RowPayload is an alias for RowPayloadTemplate."""
        payload = RowPayload(post_id=1, post_title="Test")
        assert isinstance(payload, RowPayloadTemplate)


class TestRowPayloadValidation:
    """Test payload validation functionality."""
    
    def test_validate_seo_title_too_long(self):
        """Test that SEO title over 60 chars is flagged."""
        long_title = "A" * 100
        payload = RowPayloadTemplate(
            post_id=1,
            post_title="Test",
            seo_title=long_title
        )
        
        errors = payload.validate()
        
        assert any("SEO title" in e for e in errors)
    
    def test_validate_meta_description_too_long(self):
        """Test that meta description over 160 chars is flagged."""
        long_desc = "A" * 200
        payload = RowPayloadTemplate(
            post_id=1,
            post_title="Test",
            meta_description=long_desc
        )
        
        errors = payload.validate()
        
        assert any("Meta description" in e for e in errors)
    
    def test_validate_url_slug_with_spaces(self):
        """Test that URL slug with spaces is flagged."""
        payload = RowPayloadTemplate(
            post_id=1,
            post_title="Test",
            url_slug="invalid slug"
        )
        
        errors = payload.validate()
        
        assert any("slug" in e.lower() for e in errors)
    
    def test_validate_url_slug_not_lowercase(self):
        """Test that uppercase URL slug is flagged."""
        payload = RowPayloadTemplate(
            post_id=1,
            post_title="Test",
            url_slug="Invalid-Slug"
        )
        
        errors = payload.validate()
        
        assert any("lowercase" in e.lower() for e in errors)
    
    def test_validate_word_count_below_minimum(self):
        """Test that low word count is flagged."""
        payload = RowPayloadTemplate(
            post_id=1,
            post_title="Test",
            word_count=100
        )
        
        errors = payload.validate()
        
        assert any("Word count" in e for e in errors)
    
    def test_is_valid_returns_true_for_valid_payload(self):
        """Test is_valid returns True for valid payload."""
        payload = RowPayloadTemplate(
            post_id=1,
            post_title="Test",
            seo_title="Valid Title",
            meta_description="Valid description",
            url_slug="valid-slug",
            word_count=500
        )
        
        assert payload.is_valid() == True
    
    def test_is_valid_returns_false_for_invalid_payload(self):
        """Test is_valid returns False for invalid payload."""
        payload = RowPayloadTemplate(
            post_id=1,
            post_title="Test",
            seo_title="A" * 100  # Too long
        )
        
        assert payload.is_valid() == False


class TestPayloadValidator:
    """Test PayloadValidator class."""
    
    def test_validator_validate_returns_dict(self):
        """Test that validator.validate returns a dict."""
        payload = RowPayloadTemplate(post_id=1, post_title="Test")
        validator = PayloadValidator()
        
        result = validator.validate(payload)
        
        assert isinstance(result, dict)
    
    def test_validator_is_valid(self):
        """Test validator.is_valid method."""
        payload = RowPayloadTemplate(
            post_id=1,
            post_title="Test",
            seo_title="Valid"
        )
        validator = PayloadValidator()
        
        assert validator.is_valid(payload) == True
    
    def test_validator_add_custom_rule(self):
        """Test adding custom validation rule."""
        payload = RowPayloadTemplate(post_id=1, post_title="")
        validator = PayloadValidator()
        
        # Add rule that requires non-empty title
        validator.add_rule(ValidationRule(
            "post_title",
            lambda x: x is not None and len(x) > 0,
            "Post title is required"
        ))
        
        errors = validator.validate(payload)
        assert "post_title" in errors


class TestValidationRule:
    """Test ValidationRule class."""
    
    def test_validation_rule_creation(self):
        """Test creating a validation rule."""
        rule = ValidationRule(
            field_name="test_field",
            validator=lambda x: x is not None,
            error_message="Field is required"
        )
        
        assert rule.field_name == "test_field"
        assert rule.error_message == "Field is required"
    
    def test_validation_rule_validate_method(self):
        """Test validation rule validate method."""
        rule = ValidationRule(
            field_name="test",
            validator=lambda x: len(str(x)) <= 10,
            error_message="Too long"
        )
        
        assert rule.validate("short") == True
        assert rule.validate("this is way too long") == False
    
    def test_validation_rule_default_message(self):
        """Test validation rule generates default message."""
        rule = ValidationRule(
            field_name="my_field",
            validator=lambda x: True
        )
        
        assert "my_field" in rule.error_message


class TestRowPayloadEnrichment:
    """Test payload enrichment functionality."""
    
    def test_enrich_with_seo_data(self):
        """Test enriching payload with SEO data."""
        payload = RowPayloadTemplate(
            post_id=1,
            post_title="Original Title"
        )
        
        enrichment_data = {
            "seo_title": "SEO Optimized Title",
            "meta_description": "Optimized meta description",
            "focus_keyword": "primary keyword"
        }
        
        payload.enrich(enrichment_data)
        
        assert payload.seo_title == "SEO Optimized Title"
        assert payload.meta_description == "Optimized meta description"
        assert payload.focus_keyword == "primary keyword"
    
    def test_enrich_preserves_original(self):
        """Test that enrichment preserves original data."""
        payload = RowPayloadTemplate(
            post_id=1,
            post_title="Original Title",
            post_content="Original content"
        )
        
        enrichment_data = {
            "seo_title": "New SEO Title"
        }
        
        payload.enrich(enrichment_data)
        
        # Original data preserved
        assert payload.post_title == "Original Title"
        assert payload.post_content == "Original content"
        # New data added
        assert payload.seo_title == "New SEO Title"
    
    def test_enrich_with_schema_markup(self):
        """Test enriching with schema markup."""
        payload = RowPayloadTemplate(
            post_id=1,
            post_title="Test"
        )
        
        schema_data = {
            "schema_type": "Article",
            "schema_markup": '{"@type":"Article","headline":"Test"}'
        }
        
        payload.enrich(schema_data)
        
        assert payload.schema_type == "Article"
        assert "@type" in payload.schema_markup
    
    def test_enrich_stores_unknown_fields_in_extra_data(self):
        """Test that unknown fields are stored in extra_data."""
        payload = RowPayloadTemplate(post_id=1, post_title="Test")
        
        payload.enrich({"custom_field": "custom_value"})
        
        assert "custom_field" in payload.extra_data
        assert payload.extra_data["custom_field"] == "custom_value"


class TestRowPayloadFromDict:
    """Test creating payload from dictionary."""
    
    def test_from_dict_with_known_fields(self):
        """Test from_dict with known fields."""
        data = {
            "post_id": 1,
            "post_title": "Test",
            "seo_title": "SEO Test"
        }
        
        payload = RowPayloadTemplate.from_dict(data)
        
        assert payload.post_id == 1
        assert payload.post_title == "Test"
        assert payload.seo_title == "SEO Test"
    
    def test_from_dict_with_unknown_fields(self):
        """Test from_dict stores unknown fields in extra_data."""
        data = {
            "post_id": 1,
            "post_title": "Test",
            "unknown_field": "value"
        }
        
        payload = RowPayloadTemplate.from_dict(data)
        
        assert "unknown_field" in payload.extra_data


class TestRowPayloadQualityScore:
    """Test quality score calculation."""
    
    def test_calculate_quality_score_empty_payload(self):
        """Test quality score for empty payload is 0."""
        payload = RowPayloadTemplate()
        
        score = payload.calculate_quality_score()
        
        assert score == 0.0
    
    def test_calculate_quality_score_with_word_count(self):
        """Test quality score includes word count."""
        payload = RowPayloadTemplate(
            post_id=1,
            post_title="Test",
            word_count=2500
        )
        
        score = payload.calculate_quality_score()
        
        assert score > 0
    
    def test_calculate_quality_score_with_flesch(self):
        """Test quality score includes flesch reading ease."""
        payload = RowPayloadTemplate(
            post_id=1,
            post_title="Test",
            word_count=2000,
            flesch_reading_ease=70.0
        )
        
        score = payload.calculate_quality_score()
        
        assert score > 0


class TestRowPayloadFailureMode:
    """Test payload failure mode handling."""
    
    def test_get_failure_mode_no_errors(self):
        """Test get_failure_mode returns None when no errors."""
        payload = RowPayloadTemplate(post_id=1, post_title="Test")
        
        assert payload.get_failure_mode() is None
    
    def test_get_failure_mode_api_failure(self):
        """Test get_failure_mode detects API failure."""
        payload = RowPayloadTemplate(
            post_id=1,
            post_title="Test",
            processing_errors=["API call failed", "Other error"]
        )
        
        assert payload.get_failure_mode() == "API_FAILURE"
    
    def test_get_failure_mode_timeout(self):
        """Test get_failure_mode detects timeout."""
        payload = RowPayloadTemplate(
            post_id=1,
            post_title="Test",
            processing_errors=["Request timeout exceeded"]
        )
        
        assert payload.get_failure_mode() == "TIMEOUT"
    
    def test_get_failure_mode_generic_error(self):
        """Test get_failure_mode returns generic error."""
        payload = RowPayloadTemplate(
            post_id=1,
            post_title="Test",
            processing_errors=["Something went wrong"]
        )
        
        assert payload.get_failure_mode() == "PROCESSING_ERROR"


class TestRowPayloadExtendedColumns:
    """Test extended column functionality."""
    
    def test_serp_snapshot_storage(self):
        """Test SERP snapshot storage in payload."""
        payload = RowPayloadTemplate(post_id=1, post_title="Test")
        
        payload.enrich({"serp_snapshot_raw": '{"positions": [...]}'})
        
        assert payload.serp_snapshot_raw is not None
    
    def test_paa_extraction_storage(self):
        """Test PAA (People Also Ask) extraction storage."""
        payload = RowPayloadTemplate(
            post_id=1,
            post_title="Test",
            paa_extraction=["Question 1?", "Question 2?"]
        )
        
        assert len(payload.paa_extraction) == 2
    
    def test_entity_data_storage(self):
        """Test entity/knowledge graph data storage."""
        payload = RowPayloadTemplate(
            post_id=1,
            post_title="Test",
            primary_entity_mid="/m/0jkg",
            about_schema_urls=["https://schema.org/Article"]
        )
        
        assert payload.primary_entity_mid == "/m/0jkg"
        assert len(payload.about_schema_urls) == 1
    
    def test_passage_optimization_storage(self):
        """Test passage optimization data storage."""
        payload = RowPayloadTemplate(
            post_id=1,
            post_title="Test",
            bluf_paragraph="Bottom Line Up Front content",
            snippet_bait_block="Optimized for featured snippet"
        )
        
        assert payload.bluf_paragraph == "Bottom Line Up Front content"
        assert payload.snippet_bait_block == "Optimized for featured snippet"


# Fixtures
@pytest.fixture
def sample_payload():
    """Create a sample payload for testing."""
    return RowPayloadTemplate(
        post_id=123,
        post_title="Sample Test Post",
        post_content="This is sample content for testing.",
        seo_title="Sample SEO Title | Brand",
        meta_description="A sample meta description for testing purposes.",
        focus_keyword="sample keyword",
        url_slug="sample-test-post",
        word_count=500
    )


@pytest.fixture
def empty_payload():
    """Create an empty payload for testing."""
    return create_empty_payload()


class TestWithFixtures:
    """Tests using pytest fixtures."""
    
    def test_sample_payload_is_valid(self, sample_payload):
        """Test that sample payload passes validation."""
        assert sample_payload.is_valid() == True
    
    def test_sample_payload_serialization(self, sample_payload):
        """Test serialization of sample payload."""
        json_str = sample_payload.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["post_id"] == 123
        assert parsed["focus_keyword"] == "sample keyword"
    
    def test_empty_payload_has_defaults(self, empty_payload):
        """Test that empty payload has default values."""
        assert empty_payload.post_id is None
        assert empty_payload.post_title == ""
        assert empty_payload.secondary_keywords == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
