"""
Tests for SEO validators and scoring engine.
"""
import pytest
from dataclasses import dataclass
from typing import Dict, Any, Optional


# Mock validation result class
@dataclass
class ValidationResult:
    is_valid: bool
    score: float = 0.0
    errors: list = None
    warnings: list = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


# Mock TechnicalSEOValidator for testing
class TechnicalSEOValidator:
    """Mock validator for technical SEO checks."""
    
    def validate_canonical_url(self, url: str) -> ValidationResult:
        """Validate canonical URL format."""
        if not url or not isinstance(url, str):
            return ValidationResult(is_valid=False, score=0.0, errors=["URL is empty or invalid"])
        
        if url.startswith("http://") or url.startswith("https://"):
            return ValidationResult(is_valid=True, score=1.0)
        
        return ValidationResult(is_valid=False, score=0.0, errors=["URL must start with http:// or https://"])
    
    def validate_robots_txt(self, content: str) -> ValidationResult:
        """Validate robots.txt content."""
        if "User-agent" in content:
            return ValidationResult(is_valid=True, score=0.9)
        return ValidationResult(is_valid=False, score=0.0, errors=["Missing User-agent directive"])
    
    def validate_sitemap(self, sitemap_url: str) -> ValidationResult:
        """Validate sitemap URL."""
        if sitemap_url.endswith(".xml"):
            return ValidationResult(is_valid=True, score=1.0)
        return ValidationResult(is_valid=False, score=0.5, warnings=["Sitemap should end with .xml"])


# Mock OnPageSEOValidator for testing
class OnPageSEOValidator:
    """Mock validator for on-page SEO checks."""
    
    def validate_keyword_density(self, density: float) -> ValidationResult:
        """Validate keyword density (optimal range 1-3%)."""
        if 0.01 <= density <= 0.03:
            return ValidationResult(is_valid=True, score=0.9 + (0.03 - density) * 5)
        elif 0.005 <= density < 0.01:
            return ValidationResult(is_valid=True, score=0.6, warnings=["Keyword density is low"])
        elif 0.03 < density <= 0.05:
            return ValidationResult(is_valid=True, score=0.5, warnings=["Keyword density is high"])
        else:
            return ValidationResult(is_valid=False, score=0.2, errors=["Keyword density out of acceptable range"])
    
    def validate_title_length(self, title: str) -> ValidationResult:
        """Validate title tag length (optimal 30-65 chars)."""
        length = len(title)
        if 30 <= length <= 65:
            return ValidationResult(is_valid=True, score=1.0)
        elif length < 30:
            return ValidationResult(is_valid=True, score=0.7, warnings=["Title is slightly short"])
        elif 65 < length <= 80:
            return ValidationResult(is_valid=True, score=0.7, warnings=["Title is slightly long"])
        else:
            return ValidationResult(is_valid=False, score=0.3, errors=["Title length is not optimal"])
    
    def validate_meta_description(self, description: str) -> ValidationResult:
        """Validate meta description length (optimal 100-160 chars)."""
        length = len(description)
        if 100 <= length <= 160:
            return ValidationResult(is_valid=True, score=1.0)
        elif 80 <= length < 100:
            return ValidationResult(is_valid=True, score=0.8, warnings=["Meta description is slightly short"])
        elif 160 < length <= 180:
            return ValidationResult(is_valid=True, score=0.8, warnings=["Meta description is slightly long"])
        else:
            return ValidationResult(is_valid=False, score=0.4, errors=["Meta description length is not optimal"])


# Mock ScoringEngine for testing
class ScoringEngine:
    """Mock scoring engine for aggregating SEO scores."""
    
    def aggregate_scores(self, scores: Dict[str, float]) -> float:
        """Aggregate multiple SEO scores into overall score."""
        if not scores:
            return 0.0
        
        weights = {
            "technical": 0.25,
            "onpage": 0.30,
            "offpage": 0.20,
            "content": 0.25
        }
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for category, score in scores.items():
            weight = weights.get(category, 0.2)
            weighted_sum += score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        overall = weighted_sum / total_weight
        return round(max(0.0, min(1.0, overall)), 3)
    
    def calculate_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"
    
    def get_recommendations(self, scores: Dict[str, float]) -> list:
        """Generate recommendations based on scores."""
        recommendations = []
        
        thresholds = {
            "technical": ("Technical SEO improvements needed", 0.7),
            "onpage": ("On-page optimization required", 0.7),
            "offpage": ("Backlink building recommended", 0.6),
            "content": ("Content quality enhancement needed", 0.75)
        }
        
        for category, score in scores.items():
            if category in thresholds:
                msg, threshold = thresholds[category]
                if score < threshold:
                    recommendations.append(f"{msg} (current: {score:.2f})")
        
        return recommendations


# Test cases
def test_validate_canonical_url_valid():
    validator = TechnicalSEOValidator()
    result = validator.validate_canonical_url("https://example.com/page")
    assert result.is_valid == True
    assert result.score == 1.0


def test_validate_canonical_url_invalid():
    validator = TechnicalSEOValidator()
    result = validator.validate_canonical_url("not-a-url")
    assert result.is_valid == False
    assert len(result.errors) > 0


def test_validate_canonical_url_empty():
    validator = TechnicalSEOValidator()
    result = validator.validate_canonical_url("")
    assert result.is_valid == False


def test_validate_robots_txt_valid():
    validator = TechnicalSEOValidator()
    result = validator.validate_robots_txt("User-agent: *\nDisallow: /admin")
    assert result.is_valid == True


def test_validate_sitemap_valid():
    validator = TechnicalSEOValidator()
    result = validator.validate_sitemap("https://example.com/sitemap.xml")
    assert result.is_valid == True


def test_validate_sitemap_invalid():
    validator = TechnicalSEOValidator()
    result = validator.validate_sitemap("https://example.com/sitemap.html")
    assert result.is_valid == False
    assert len(result.warnings) > 0


def test_validate_keyword_density_optimal():
    validator = OnPageSEOValidator()
    result = validator.validate_keyword_density(0.02)  # 2%
    assert result.is_valid == True
    assert result.score > 0.8


def test_validate_keyword_density_low():
    validator = OnPageSEOValidator()
    result = validator.validate_keyword_density(0.005)  # 0.5%
    assert result.is_valid == True
    assert len(result.warnings) > 0


def test_validate_keyword_density_high():
    validator = OnPageSEOValidator()
    result = validator.validate_keyword_density(0.04)  # 4%
    assert result.is_valid == True
    assert len(result.warnings) > 0


def test_validate_keyword_density_invalid():
    validator = OnPageSEOValidator()
    result = validator.validate_keyword_density(0.10)  # 10%
    assert result.is_valid == False


def test_validate_title_length_optimal():
    validator = OnPageSEOValidator()
    result = validator.validate_title_length("Best SEO Tools for 2024 - Comprehensive Guide")
    assert result.is_valid == True
    assert result.score == 1.0


def test_validate_title_length_short():
    validator = OnPageSEOValidator()
    result = validator.validate_title_length("SEO Tools")
    assert result.is_valid == True
    assert len(result.warnings) > 0


def test_validate_title_length_long():
    validator = OnPageSEOValidator()
    result = validator.validate_title_length("Best SEO Tools for 2024 - Comprehensive Guide and Review for Digital Marketers")
    assert result.is_valid == True
    assert len(result.warnings) > 0


def test_validate_meta_description_optimal():
    validator = OnPageSEOValidator()
    desc = "Discover the best SEO tools for 2024. Our comprehensive guide covers everything you need to improve rankings."
    result = validator.validate_meta_description(desc)
    assert result.is_valid == True
    assert result.score == 1.0


def test_scoring_engine_aggregation():
    engine = ScoringEngine()
    scores = {"technical": 0.8, "onpage": 0.7, "offpage": 0.6}
    overall = engine.aggregate_scores(scores)
    assert 0 <= overall <= 1


def test_scoring_engine_aggregation_with_all_categories():
    engine = ScoringEngine()
    scores = {"technical": 0.9, "onpage": 0.85, "offpage": 0.7, "content": 0.8}
    overall = engine.aggregate_scores(scores)
    assert 0.7 <= overall <= 1.0


def test_scoring_engine_empty_scores():
    engine = ScoringEngine()
    overall = engine.aggregate_scores({})
    assert overall == 0.0


def test_scoring_engine_calculate_grade():
    engine = ScoringEngine()
    assert engine.calculate_grade(0.95) == "A"
    assert engine.calculate_grade(0.85) == "B"
    assert engine.calculate_grade(0.75) == "C"
    assert engine.calculate_grade(0.65) == "D"
    assert engine.calculate_grade(0.5) == "F"


def test_scoring_engine_recommendations():
    engine = ScoringEngine()
    scores = {"technical": 0.6, "onpage": 0.8, "offpage": 0.5, "content": 0.7}
    recommendations = engine.get_recommendations(scores)
    assert len(recommendations) >= 2
