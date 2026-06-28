"""
Row Payload Template for SEO/GEO Framework.
Contains core and extended fields used across parsing and automation pipelines.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any, Callable, Dict, List, Optional


class PayloadStatus(Enum):
    """Status enum for payload processing states."""
    EMPTY = "empty"
    VALID = "valid"
    INVALID = "invalid"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ValidationRule:
    """Validation rule for payload fields."""
    def __init__(self, field_name: str, validator: Callable[[Any], bool], 
                 error_message: str = ""):
        self.field_name = field_name
        self.validator = validator
        self.error_message = error_message or f"Validation failed for {field_name}"
    
    def validate(self, value: Any) -> bool:
        return self.validator(value)


class PayloadValidator:
    """Validator class for RowPayloadTemplate."""
    
    def __init__(self):
        self.rules: List[ValidationRule] = []
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default validation rules."""
        self.rules = [
            ValidationRule(
                "seo_title",
                lambda x: x is None or len(str(x)) <= 60,
                "SEO title exceeds 60 characters"
            ),
            ValidationRule(
                "meta_description",
                lambda x: x is None or len(str(x)) <= 160,
                "Meta description exceeds 160 characters"
            ),
            ValidationRule(
                "post_title",
                lambda x: x is not None and len(str(x)) > 0,
                "Post title is required"
            ),
        ]
    
    def add_rule(self, rule: ValidationRule):
        """Add a custom validation rule."""
        self.rules.append(rule)
    
    def validate(self, payload: 'RowPayloadTemplate') -> Dict[str, List[str]]:
        """Validate a payload and return errors by field."""
        errors: Dict[str, List[str]] = {}
        for rule in self.rules:
            value = getattr(payload, rule.field_name, None)
            if not rule.validate(value):
                if rule.field_name not in errors:
                    errors[rule.field_name] = []
                errors[rule.field_name].append(rule.error_message)
        return errors
    
    def is_valid(self, payload: 'RowPayloadTemplate') -> bool:
        """Check if payload is valid."""
        return len(self.validate(payload)) == 0


def create_empty_payload() -> 'RowPayloadTemplate':
    """Create an empty payload with default values."""
    return RowPayloadTemplate()


def create_payload_from_dict(data: Dict[str, Any]) -> 'RowPayloadTemplate':
    """Create a payload from a dictionary."""
    return RowPayloadTemplate.from_dict(data)


@dataclass
class RowPayloadTemplate:
    """SEO/GEO framework row payload."""

    # WordPress Core Fields
    post_id: Optional[int] = None
    post_title: Optional[str] = ""
    post_content: Optional[str] = ""
    post_excerpt: Optional[str] = ""

    # Basic SEO Fields
    seo_title: Optional[str] = None
    meta_description: Optional[str] = None
    focus_keyword: Optional[str] = None
    secondary_keywords: List[str] = field(default_factory=list)
    canonical_url: Optional[str] = None
    url_slug: Optional[str] = None

    # Schema/Structured Data
    schema_type: Optional[str] = None
    schema_markup: Optional[str] = None
    schema_validation_status: Optional[str] = None
    schema_errors: List[str] = field(default_factory=list)

    # Research Data
    serp_snapshot_raw: Optional[str] = None
    serp_snapshot_date: Optional[str] = None
    paa_extraction: List[str] = field(default_factory=list)
    competitor_analysis: Optional[str] = None
    content_gaps: List[str] = field(default_factory=list)
    competitor_missing_gaps: List[str] = field(default_factory=list)
    keyword_difficulty: Optional[float] = None

    # Entity/Knowledge Graph
    primary_entity_mid: Optional[str] = None
    entity_confidence: Optional[float] = None
    about_schema_urls: List[str] = field(default_factory=list)
    mentions_schema_urls: List[str] = field(default_factory=list)
    related_entities: List[Dict[str, Any]] = field(default_factory=list)

    # Passage Optimization
    bluf_paragraph: Optional[str] = None
    snippet_bait_block: Optional[str] = None
    key_takeaways: List[str] = field(default_factory=list)
    faq_section: List[Dict[str, str]] = field(default_factory=list)

    # IA Architecture
    h2_headings: List[str] = field(default_factory=list)
    h2_questions: List[str] = field(default_factory=list)
    h2_structure: Optional[List[str]] = None
    target_url: Optional[str] = None
    table_of_contents: Optional[str] = None
    internal_links: List[Dict[str, str]] = field(default_factory=list)
    external_links: List[Dict[str, str]] = field(default_factory=list)

    # Media
    featured_image_url: Optional[str] = None
    featured_image_alt: Optional[str] = None
    discover_image_url: Optional[str] = None
    discover_image_alt: Optional[str] = None
    image_prompts: List[str] = field(default_factory=list)
    video_urls: List[str] = field(default_factory=list)

    # Quality Metrics
    word_count: Optional[int] = None
    word_count_target: Optional[int] = None
    reading_time: Optional[int] = None
    flesch_reading_ease: Optional[float] = None
    ai_detection_score: Optional[float] = None
    plagiarism_score: Optional[float] = None
    quality_score: Optional[float] = None

    # GEO Signals
    geo_relevance_score: Optional[float] = None
    target_cities: List[str] = field(default_factory=list)
    is_cornerstone: Optional[bool] = None
    citation_count: Optional[int] = None
    source_diversity_score: Optional[float] = None
    fact_check_status: Optional[str] = None
    author_credibility: Optional[float] = None
    e_e_a_t_score: Optional[float] = None

    # Backlink Data
    backlink_count: Optional[int] = None
    referring_domains: Optional[int] = None
    domain_authority: Optional[float] = None
    page_authority: Optional[float] = None
    spam_score: Optional[float] = None
    backlink_quality_score: Optional[float] = None

    # Performance Tracking
    organic_clicks: Optional[int] = None
    impressions: Optional[int] = None
    ctr: Optional[float] = None
    avg_position: Optional[float] = None
    best_position: Optional[int] = None
    position_change: Optional[float] = None

    # Workflow Status
    workflow_stage: Optional[str] = None
    last_processed: Optional[str] = None
    processing_errors: List[str] = field(default_factory=list)
    retry_count: Optional[int] = None
    locked_by: Optional[str] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        if self.created_at is None:
            self.created_at = now
        self.updated_at = now

    def validate(self) -> List[str]:
        errors: List[str] = []

        if self.seo_title and len(self.seo_title) > 60:
            errors.append("SEO title exceeds 60 characters")

        if self.meta_description and len(self.meta_description) > 160:
            errors.append("Meta description exceeds 160 characters")

        if self.url_slug:
            if " " in self.url_slug:
                errors.append("URL slug contains spaces")
            if self.url_slug != self.url_slug.lower():
                errors.append("URL slug should be lowercase")

        if self.word_count is not None and self.word_count < 300:
            errors.append("Word count below minimum threshold (300)")

        return errors

    def is_valid(self) -> bool:
        return len(self.validate()) == 0

    def enrich(self, data: Dict[str, Any]) -> None:
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.extra_data[key] = value
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RowPayloadTemplate":
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        unknown = {k: v for k, v in data.items() if k not in cls.__dataclass_fields__}
        obj = cls(**known)
        if unknown:
            obj.extra_data.update(unknown)
        return obj

    def get_failure_mode(self) -> Optional[str]:
        if self.processing_errors:
            if any("api" in e.lower() for e in self.processing_errors):
                return "API_FAILURE"
            if any("timeout" in e.lower() for e in self.processing_errors):
                return "TIMEOUT"
            return "PROCESSING_ERROR"
        return None

    def calculate_quality_score(self) -> float:
        scores: List[tuple[str, float]] = []
        weights = {
            "word_count": 0.15,
            "flesch_reading_ease": 0.15,
            "ai_detection_score": 0.20,
            "e_e_a_t_score": 0.20,
            "geo_relevance_score": 0.15,
            "citation_count": 0.15,
        }

        if self.word_count and self.word_count >= 2000:
            scores.append(("word_count", 100.0))
        elif self.word_count and self.word_count >= 1000:
            scores.append(("word_count", 70.0))
        elif self.word_count:
            scores.append(("word_count", 40.0))

        if self.flesch_reading_ease is not None:
            scores.append(("flesch_reading_ease", min(100.0, self.flesch_reading_ease)))

        if self.ai_detection_score is not None:
            scores.append(("ai_detection_score", max(0.0, 100.0 - (self.ai_detection_score * 100.0))))

        if self.e_e_a_t_score is not None:
            scores.append(("e_e_a_t_score", self.e_e_a_t_score * 100.0))

        if self.geo_relevance_score is not None:
            scores.append(("geo_relevance_score", self.geo_relevance_score * 100.0))

        if self.citation_count is not None:
            scores.append(("citation_count", min(100.0, self.citation_count * 10.0)))

        if not scores:
            return 0.0

        total_weight = sum(weights.get(name, 0.1) for name, _ in scores)
        weighted_sum = sum(weights.get(name, 0.1) * value for name, value in scores)
        if total_weight <= 0:
            return 0.0
        return round(weighted_sum / total_weight, 2)


# Compatibility alias expected by parser/test modules.
RowPayload = RowPayloadTemplate
