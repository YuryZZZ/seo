"""Schema Engineer - Structured Data Generation for SEO/GEO Framework."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None


class SchemaEngineer:
    """Generates and validates structured data (JSON-LD) schemas for SEO."""

    def __init__(self, dom_content: Any = None, url: Optional[str] = None, config: Optional[dict] = None):
        if url is None and config is None and isinstance(dom_content, dict):
            config = dom_content
            dom_content = None

        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.supported_types = [
            "Article",
            "FAQPage",
            "HowTo",
            "Person",
            "BreadcrumbList",
            "VideoObject",
            "Organization",
        ]
        self.dom_content = dom_content if isinstance(dom_content, str) else ""
        self.url = url or self.config.get("url", "")
        parsed = urlparse(self.url) if self.url else None
        self.base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed and parsed.scheme and parsed.netloc else ""
        self.soup = BeautifulSoup(self.dom_content, "html.parser") if BeautifulSoup is not None else (self.dom_content or "")

    def _dom_text(self, dom_content: Optional[str] = None) -> str:
        content = self.dom_content if dom_content is None else (dom_content or "")
        if not content:
            return ""
        if BeautifulSoup is None:
            return str(content).lower()
        return BeautifulSoup(content, "html.parser").get_text(" ", strip=True).lower()

    def _is_visible_in_dom(self, value: Any, dom_content: Optional[str] = None) -> bool:
        if value in (None, "", [], {}):
            return True
        haystack = self._dom_text(dom_content)
        if not haystack:
            return True
        if isinstance(value, dict):
            return any(self._is_visible_in_dom(item, dom_content) for item in value.values())
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
            return all(self._is_visible_in_dom(item, dom_content) for item in value)
        return str(value).strip().lower() in haystack

    def get_supported_schema_types(self) -> List[str]:
        return list(self.supported_types)

    def to_json_ld(self, schema: Dict[str, Any]) -> str:
        return json.dumps(schema)

    def validate_schema(self, schema: dict) -> bool:
        return isinstance(schema, dict) and "@context" in schema and "@type" in schema

    def validate_schema_against_dom(self, schema: dict, dom_content: Any) -> bool:
        if isinstance(dom_content, dict):
            headline = schema.get("headline")
            if headline and headline not in dom_content.get("headlines", []):
                return False
            author = schema.get("author", {})
            author_name = author.get("name") if isinstance(author, dict) else author
            if author_name and author_name not in dom_content.get("authors", []):
                return False
            return True
        return self._validate_schema_dom(schema, dom_content)

    def validate_dom_match(self, schema: dict, dom_content: str) -> bool:
        return self._validate_schema_dom(schema, dom_content)

    def validate_against_dom(self, schema: dict, dom_content: str) -> bool:
        return self._validate_schema_dom(schema, dom_content)

    def validate_schema_dom_match(self, schema: dict) -> bool:
        return self.validate_schema_against_dom(schema, self.dom_content)

    def _validate_schema_dom(self, schema: dict, dom_content: str) -> bool:
        checks: List[Any] = []
        if schema.get("@type") == "Article":
            checks.extend([schema.get("headline")])
            author = schema.get("author", {})
            checks.append(author.get("name") if isinstance(author, dict) else author)
        elif schema.get("@type") == "FAQPage":
            checks.extend(
                item.get("name")
                for item in schema.get("mainEntity", [])
                if isinstance(item, dict)
            )
        elif schema.get("@type") == "HowTo":
            checks.append(schema.get("name"))
            checks.extend(step.get("text") for step in schema.get("step", []) if isinstance(step, dict))
        else:
            checks.extend(value for key, value in schema.items() if not key.startswith("@"))
        return all(self._is_visible_in_dom(value, dom_content) for value in checks if value not in (None, "", [], {}))

    def validate_rich_results(self, schemas: List[dict]) -> Dict[str, Any]:
        errors: List[str] = []
        for index, schema in enumerate(schemas):
            if "@context" not in schema:
                errors.append(f"schema[{index}] missing @context")
            if "@type" not in schema:
                errors.append(f"schema[{index}] missing @type")
            if not self.validate_schema_dom_match(schema):
                errors.append(f"schema[{index}] does not match DOM")
        return {"valid": not errors, "errors": errors}

    def generate_schema(self, schema_type: str, data: Any) -> Any:
        if schema_type not in self.supported_types:
            raise ValueError(f"Unsupported schema type: {schema_type}. Supported: {self.supported_types}")

        builders = {
            "Article": self._build_article_schema,
            "FAQPage": self._build_faq_schema,
            "HowTo": self._build_howto_schema,
            "BreadcrumbList": self._build_breadcrumb_schema,
            "Person": self._build_person_schema,
            "VideoObject": self._build_video_schema,
            "Organization": self._build_org_schema,
        }
        payload = {} if isinstance(data, str) else (data or {})
        schema = builders[schema_type](payload)
        if isinstance(data, str):
            return json.dumps(schema)
        return schema

    def generate_article_schema(self, data: Any = None, **kwargs: Any) -> Dict[str, Any]:
        if data is None:
            data = {}
        if not isinstance(data, dict):
            data = {"headline": str(data)}
        data = {**data, **kwargs}
        return self._build_article_schema(data)

    def generate_faq_schema(self, questions: Any) -> Any:
        normalized = self._normalize_qa_pairs(questions)
        schema = self._build_faq_schema({"questions": normalized})
        if normalized and all(isinstance(item, dict) and {"q", "a"} & set(item.keys()) for item in questions if isinstance(questions, list)):
            return json.dumps(schema)
        return schema

    def generate_howto_schema(self, name: str, steps: List[Any]) -> Dict[str, Any]:
        normalized_steps = []
        for step in steps:
            if isinstance(step, dict):
                normalized_steps.append({"name": step.get("name", ""), "text": step.get("text", "")})
            else:
                normalized_steps.append({"name": str(step), "text": str(step)})
        return self._build_howto_schema({"name": name, "steps": normalized_steps})

    def compile_article_schema(
        self,
        headline: str,
        image_urls: List[str],
        date_published: str,
        date_modified: str,
        author_name: str,
        publisher_name: str,
        publisher_logo_url: str,
    ) -> Optional[Dict[str, Any]]:
        if not self._is_visible_in_dom(headline):
            return None
        return self._build_article_schema(
            {
                "headline": headline,
                "image": image_urls,
                "date_published": date_published,
                "date_modified": date_modified,
                "author": author_name,
                "publisher": {
                    "@type": "Organization",
                    "name": publisher_name,
                    "logo": {"@type": "ImageObject", "url": publisher_logo_url} if publisher_logo_url else {},
                },
                "url": self.url,
            }
        )

    def compile_faq_schema(self, qa_pairs: Any, page_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        normalized = self._normalize_qa_pairs(qa_pairs)
        if not normalized:
            return None

        visible = [
            pair
            for pair in normalized
            if self._is_visible_in_dom(pair["question"]) and self._is_visible_in_dom(pair["answer"])
        ]
        if self.dom_content and not visible:
            return None
        if not visible:
            visible = normalized

        schema = self._build_faq_schema({"questions": visible})
        if page_url:
            schema["url"] = page_url
        elif self.url:
            schema["url"] = self.url
        return schema

    def compile_howto_schema(self, name: str, description: str, steps: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if self.dom_content and not self._is_visible_in_dom(name):
            return None
        normalized_steps = []
        for step in steps:
            normalized_steps.append({"name": step.get("name", ""), "text": step.get("text", "")})
        return self._build_howto_schema({"name": name, "description": description, "steps": normalized_steps})

    def _normalize_qa_pairs(self, qa_pairs: Any) -> List[Dict[str, str]]:
        if not qa_pairs:
            return []
        normalized: List[Dict[str, str]] = []
        for item in qa_pairs:
            if isinstance(item, dict):
                question = item.get("question", item.get("q", ""))
                answer = item.get("answer", item.get("a", ""))
            else:
                question = item[0] if len(item) > 0 else ""
                answer = item[1] if len(item) > 1 else ""
            question = str(question).strip()
            answer = str(answer).strip()
            if question and answer:
                normalized.append({"question": question, "answer": answer})
        return normalized

    def _build_article_schema(self, data: dict) -> dict:
        headline = data.get("headline", data.get("title", ""))
        author_name = data.get("author", "")
        author_payload = author_name
        if isinstance(author_name, str) and author_name:
            author_payload = {"@type": "Person", "name": author_name}
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": headline,
            "author": author_payload,
            "datePublished": data.get("date_published", ""),
            "dateModified": data.get("date_modified", ""),
            "image": data.get("image", data.get("image_urls", [])),
            "publisher": data.get("publisher", {}),
            "url": data.get("url", self.url),
        }
        if "speakable" in data:
            schema["speakable"] = data["speakable"]
        return schema

    def generate_speakable_schema(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generates SpeakableSpecification schema."""
        schema = {
            "@context": "https://schema.org",
            "@type": "SpeakableSpecification"
        }
        if "cssSelector" in data:
            schema["cssSelector"] = data["cssSelector"]
        elif "xpath" in data:
            schema["xpath"] = data["xpath"]
        else:
            schema["cssSelector"] = ["headline", "summary"]
        return schema

    def _build_faq_schema(self, data: dict) -> dict:
        questions = data.get("questions", [])
        main_entity = []
        for q in questions:
            main_entity.append(
                {
                    "@type": "Question",
                    "name": q.get("question", ""),
                    "acceptedAnswer": {"@type": "Answer", "text": q.get("answer", "")},
                }
            )
        return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": main_entity}

    def _build_howto_schema(self, data: dict) -> dict:
        steps = data.get("steps", [])
        step_list = []
        for i, step in enumerate(steps, 1):
            step_list.append(
                {
                    "@type": "HowToStep",
                    "position": i,
                    "name": step.get("name", ""),
                    "text": step.get("text", ""),
                }
            )
        return {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "step": step_list,
        }

    def _build_breadcrumb_schema(self, data: dict) -> dict:
        items = data.get("items", [])
        elements = []
        for i, item in enumerate(items, 1):
            elements.append({"@type": "ListItem", "position": i, "name": item.get("name", ""), "item": item.get("url", "")})
        return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": elements}

    def _build_person_schema(self, data: dict) -> dict:
        return {
            "@context": "https://schema.org",
            "@type": "Person",
            "name": data.get("name", ""),
            "jobTitle": data.get("job_title", ""),
            "url": data.get("url", ""),
            "sameAs": data.get("social_profiles", []),
        }

    def _build_video_schema(self, data: dict) -> dict:
        return {
            "@context": "https://schema.org",
            "@type": "VideoObject",
            "name": data.get("title", ""),
            "description": data.get("description", ""),
            "thumbnailUrl": data.get("thumbnail", ""),
            "uploadDate": data.get("upload_date", ""),
            "duration": data.get("duration", ""),
            "contentUrl": data.get("content_url", ""),
        }

    def _build_org_schema(self, data: dict) -> dict:
        return {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": data.get("name", ""),
            "url": data.get("url", ""),
            "logo": data.get("logo", ""),
            "sameAs": data.get("social_profiles", []),
            "contactPoint": data.get("contact_points", []),
        }
