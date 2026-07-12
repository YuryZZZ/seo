"""Tests for SchemaGenerator — JSON-LD structured data generation."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import pytest
from schema_generator import SchemaGenerator


class TestArticleSchema:
    """Test Article/BlogPosting schema generation."""

    def test_basic_article(self):
        schema = SchemaGenerator.generate_article_schema(headline="Test Title")
        assert schema["@context"] == "https://schema.org"
        assert schema["@type"] == "Article"
        assert schema["headline"] == "Test Title"

    def test_title_alias(self):
        schema = SchemaGenerator.generate_article_schema(title="From Title")
        assert schema["headline"] == "From Title"

    def test_blog_posting_type(self):
        schema = SchemaGenerator.generate_article_schema(type="BlogPosting", headline="Blog")
        assert schema["@type"] == "BlogPosting"

    def test_author_string_expanded(self):
        schema = SchemaGenerator.generate_article_schema(headline="T", author="John")
        assert schema["author"]["@type"] == "Person"
        assert schema["author"]["name"] == "John"

    def test_author_dict(self):
        schema = SchemaGenerator.generate_article_schema(
            headline="T",
            author={"name": "Jane", "url": "https://jane.com"}
        )
        assert schema["author"]["name"] == "Jane"
        assert schema["author"]["url"] == "https://jane.com"


class TestFAQSchema:
    """Test FAQPage schema generation."""

    def test_empty_list(self):
        schema = SchemaGenerator.generate_faq_schema([])
        assert schema["@type"] == "FAQPage"
        assert schema["mainEntity"] == []

    def test_valid_questions(self):
        questions = [
            {"question": "What is SEO?", "answer": "Search Engine Optimization."},
            {"question": "Why SEO?", "answer": "For visibility."},
        ]
        schema = SchemaGenerator.generate_faq_schema(questions)
        assert len(schema["mainEntity"]) == 2
        assert schema["mainEntity"][0]["@type"] == "Question"
        assert schema["mainEntity"][0]["name"] == "What is SEO?"
        assert schema["mainEntity"][0]["acceptedAnswer"]["@type"] == "Answer"

    def test_skips_incomplete_entries(self):
        questions = [
            {"question": "Valid?", "answer": "Yes"},
            {"question_only": "Missing answer key"},
        ]
        schema = SchemaGenerator.generate_faq_schema(questions)
        assert len(schema["mainEntity"]) == 1


class TestBreadcrumbSchema:
    """Test BreadcrumbList schema generation."""

    def test_basic_breadcrumbs(self):
        items = [
            {"name": "Home", "url": "/"},
            {"name": "Blog", "url": "/blog"},
            {"name": "SEO Guide", "url": "/blog/seo-guide"},
        ]
        schema = SchemaGenerator.generate_breadcrumb_schema(items)
        assert schema["@type"] == "BreadcrumbList"
        assert len(schema["itemListElement"]) == 3
        # Positions should be sequential
        positions = [item["position"] for item in schema["itemListElement"]]
        assert positions == [1, 2, 3]


class TestHowToSchema:
    """Test HowTo schema generation."""

    def test_basic_howto(self):
        data = {
            "name": "How to Do SEO",
            "description": "A step-by-step guide.",
            "steps": [
                {"name": "Research keywords", "text": "Find relevant keywords."},
                {"name": "Write content", "text": "Create optimized content."},
            ],
        }
        schema = SchemaGenerator.generate_howto_schema(data)
        assert schema["@type"] == "HowTo"
        assert schema["name"] == "How to Do SEO"
        assert "step" in schema

    def test_empty_steps(self):
        schema = SchemaGenerator.generate_howto_schema({"name": "Test"})
        assert schema["name"] == "Test"


class TestLocalBusinessSchema:
    """Test LocalBusiness schema generation."""

    def test_basic_business(self):
        data = {
            "name": "Acme SEO Agency",
            "address": {"street": "123 Main St", "city": "London"},
            "phone": "+44 1234567890",
        }
        schema = SchemaGenerator.generate_local_business_schema(data)
        assert schema["@type"] == "LocalBusiness"
        assert schema["name"] == "Acme SEO Agency"


class TestProductSchema:
    """Test Product schema generation."""

    def test_basic_product(self):
        data = {
            "name": "SEO Tool Pro",
            "description": "The best SEO tool.",
            "price": "99.99",
            "currency": "USD",
        }
        schema = SchemaGenerator.generate_product_schema(data)
        assert schema["@type"] == "Product"
        assert schema["name"] == "SEO Tool Pro"


class TestSchemaValidation:
    """Test schema validation methods."""

    def test_validate_valid_schema(self):
        schema = SchemaGenerator.generate_article_schema(
            headline="Valid", image="https://example.com/img.jpg"
        )
        result = SchemaGenerator.validate_schema(schema)
        assert result["is_valid"] is True

    def test_validate_missing_context(self):
        schema = {"@type": "Article"}  # Missing @context
        result = SchemaGenerator.validate_schema(schema)
        assert result["is_valid"] is False

    def test_validate_missing_type(self):
        schema = {"@context": "https://schema.org"}  # Missing @type
        result = SchemaGenerator.validate_schema(schema)
        assert result["is_valid"] is False


class TestSchemaGraph:
    """Test schema graph merging."""

    def test_merge_schemas(self):
        article = SchemaGenerator.generate_article_schema(headline="Test")
        faq = SchemaGenerator.generate_faq_schema([
            {"question": "Q?", "answer": "A."}
        ])
        graph = SchemaGenerator.merge_schemas([article, faq])
        assert graph["@context"] == "https://schema.org"
        assert "@graph" in graph
        assert len(graph["@graph"]) == 2
