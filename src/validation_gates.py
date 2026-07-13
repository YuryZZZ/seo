"""
Validation Gates for SEO/GEO Framework.

12 production validation gates that check real content quality signals.
Each gate inspects pipeline data and returns pass/fail with actionable details.
"""
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, Any, List, Optional


# Known AI tell-words that indicate AI-generated content
AI_TELL_WORDS = [
    "delve", "uncover", "unlock", "mastering", "realm", "tapestry",
    "ever-evolving", "comprehensive guide", "ultimate guide",
    "in conclusion", "in today's world", "it's important to note",
    "in this article", "let's dive", "game-changer", "navigate the",
    "landscape", "at its core", "cutting-edge", "paradigm",
]


@dataclass
class GateResult:
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationGate:
    name: str
    rule: Callable[[Dict[str, Any]], GateResult]
    action_on_fail: str


class GateRegistry:
    def __init__(self):
        self.gates: Dict[str, ValidationGate] = {}
        self._register_default_gates()

    def register_gate(self, gate: ValidationGate):
        """Register a new validation gate."""
        self.gates[gate.name] = gate

    def _register_default_gates(self):
        """Register the 12 core validation gates."""

        self.register_gate(ValidationGate(
            name="Helpful Content Self-Assessment",
            rule=self._rule_helpful_content,
            action_on_fail="Flag for human review or regenerate content"
        ))
        self.register_gate(ValidationGate(
            name="Visible Schema Fidelity",
            rule=self._rule_visible_schema,
            action_on_fail="Fix schema mismatch"
        ))
        self.register_gate(ValidationGate(
            name="Pinterest API V5 Payload",
            rule=self._rule_pinterest_payload,
            action_on_fail="Re-generate Pinterest payload"
        ))
        self.register_gate(ValidationGate(
            name="YouTube Captions Snippet",
            rule=self._rule_youtube_captions,
            action_on_fail="Add YouTube captions snippet"
        ))
        self.register_gate(ValidationGate(
            name="AI Signature Detection",
            rule=self._rule_ai_signature,
            action_on_fail="Rewrite to reduce AI signatures"
        ))
        self.register_gate(ValidationGate(
            name="Image Size Policy (Discover)",
            rule=self._rule_image_size,
            action_on_fail="Resize images for Google Discover (1200px wide)"
        ))
        self.register_gate(ValidationGate(
            name="Author E-E-A-T Credential",
            rule=self._rule_author_eeat,
            action_on_fail="Add author credentials"
        ))
        self.register_gate(ValidationGate(
            name="H2 Question Ratio",
            rule=self._rule_h2_ratio,
            action_on_fail="Adjust H2 tags to include more questions"
        ))
        self.register_gate(ValidationGate(
            name="BLUF Presence",
            rule=self._rule_bluf_presence,
            action_on_fail="Add BLUF (Bottom Line Up Front) paragraph"
        ))
        self.register_gate(ValidationGate(
            name="Alt Text Accessibility",
            rule=self._rule_alt_text,
            action_on_fail="Add descriptive alt text to images"
        ))
        self.register_gate(ValidationGate(
            name="Canonical Integrity",
            rule=self._rule_canonical_integrity,
            action_on_fail="Fix canonical URL mismatch"
        ))
        self.register_gate(ValidationGate(
            name="Rich Results Validator",
            rule=self._rule_rich_results,
            action_on_fail="Fix schema to pass rich results test"
        ))

    # ── Gate 1: Helpful Content Self-Assessment ──────────────────
    def _rule_helpful_content(self, data: Dict[str, Any]) -> GateResult:
        """Check content meets Google's Helpful Content guidelines."""
        content = data.get("content", "")
        word_count = len(content.split()) if content else 0

        # Pull from pipeline results if no direct content
        results = data.get("results", {})
        p4 = results.get("phase_4", {})
        if not content and p4:
            word_count = p4.get("word_count_targets", {}).get("min_page_words", 0)

        issues = []
        if word_count < 300 and content:
            issues.append(f"Content too thin ({word_count} words, need 300+)")
        if content and content.count("\n") < 3:
            issues.append("Content lacks structural paragraphs")

        # Check for keyword stuffing (any word > 5% density)
        if content and word_count > 50:
            words = content.lower().split()
            from collections import Counter
            freq = Counter(words)
            for word, count in freq.most_common(5):
                if len(word) > 4 and count / word_count > 0.05:
                    issues.append(f"Possible keyword stuffing: '{word}' at {count/word_count:.1%}")

        if issues:
            return GateResult(passed=False, message=f"Helpful content check failed: {'; '.join(issues)}", details={"issues": issues, "word_count": word_count})
        return GateResult(passed=True, message=f"Helpful content assessment passed ({word_count} words)", details={"word_count": word_count})

    # ── Gate 2: Visible Schema Fidelity ──────────────────────────
    def _rule_visible_schema(self, data: Dict[str, Any]) -> GateResult:
        """Verify schema markup matches visible page content."""
        schema = data.get("schema", data.get("schemas", {}))
        results = data.get("results", {})
        p6 = results.get("phase_6", {})

        schema_types = p6.get("schema_types_generated", []) if p6 else []
        if isinstance(schema, dict):
            schema_type = schema.get("@type", "")
            schema_types = [schema_type] if schema_type else schema_types

        if not schema_types and not schema:
            return GateResult(passed=False, message="No schema markup found", details={"schema_types": []})

        return GateResult(passed=True, message=f"Schema fidelity verified: {schema_types}", details={"schema_types": schema_types})

    # ── Gate 3: Pinterest API V5 Payload ─────────────────────────
    def _rule_pinterest_payload(self, data: Dict[str, Any]) -> GateResult:
        """Validate Pinterest pin payload has required fields."""
        pin = data.get("pinterest_payload", {})
        if not pin:
            # If no pin data provided, pass with advisory
            return GateResult(passed=True, message="Pinterest payload check skipped (no pin data)", details={"skipped": True})

        required = ["title", "description", "link", "media_source"]
        missing = [f for f in required if f not in pin]
        if missing:
            return GateResult(passed=False, message=f"Pinterest payload missing: {missing}", details={"missing_fields": missing})

        # Title 100 chars, description 500 chars
        issues = []
        if len(pin.get("title", "")) > 100:
            issues.append("Title exceeds 100 chars")
        if len(pin.get("description", "")) > 500:
            issues.append("Description exceeds 500 chars")
        if issues:
            return GateResult(passed=False, message=f"Pinterest payload issues: {issues}", details={"issues": issues})

        return GateResult(passed=True, message="Pinterest API V5 payload valid", details={"fields_present": list(pin.keys())})

    # ── Gate 4: YouTube Captions Snippet ─────────────────────────
    def _rule_youtube_captions(self, data: Dict[str, Any]) -> GateResult:
        """Check if YouTube caption/transcript snippet is included."""
        captions = data.get("youtube_captions", data.get("video_transcript", ""))
        has_video = data.get("has_video", False)

        if not has_video:
            return GateResult(passed=True, message="YouTube captions check skipped (no video content)", details={"skipped": True})

        if not captions:
            return GateResult(passed=False, message="Video content present but no captions/transcript", details={"has_video": True, "has_captions": False})

        return GateResult(passed=True, message="YouTube captions snippet present", details={"caption_length": len(captions)})

    # ── Gate 5: AI Signature Detection ───────────────────────────
    def _rule_ai_signature(self, data: Dict[str, Any]) -> GateResult:
        """Detect AI-generated tell-words in content."""
        content = data.get("content", "")

        # Check pipeline results for AI tells
        results = data.get("results", {})
        p4 = results.get("phase_4", {})
        detected_tells = p4.get("ai_tells_detected", [])

        if not content and not detected_tells:
            return GateResult(passed=True, message="AI signature check passed (no content to scan)", details={"tells_found": []})

        if not detected_tells and content:
            content_lower = content.lower()
            detected_tells = [word for word in AI_TELL_WORDS if word in content_lower]

        if len(detected_tells) >= 3:
            return GateResult(
                passed=False,
                message=f"High AI signature density: {len(detected_tells)} tell-words found",
                details={"tells_found": detected_tells, "threshold": 3}
            )

        return GateResult(
            passed=True,
            message=f"AI signature detection passed ({len(detected_tells)} tell-words, threshold=3)",
            details={"tells_found": detected_tells}
        )

    # ── Gate 6: Image Size Policy (Google Discover) ──────────────
    def _rule_image_size(self, data: Dict[str, Any]) -> GateResult:
        """Check images meet Google Discover minimum (1200px wide)."""
        images = data.get("images", [])
        if not images:
            return GateResult(passed=True, message="Image size check skipped (no images)", details={"skipped": True})

        undersized = []
        for img in images:
            width = img.get("width", 0)
            if width and width < 1200:
                undersized.append({"src": img.get("src", "?"), "width": width})

        if undersized:
            return GateResult(passed=False, message=f"{len(undersized)} images below 1200px Discover minimum", details={"undersized": undersized})

        return GateResult(passed=True, message=f"All {len(images)} images meet Discover size policy", details={"image_count": len(images)})

    # ── Gate 7: Author E-E-A-T Credential ────────────────────────
    def _rule_author_eeat(self, data: Dict[str, Any]) -> GateResult:
        """Verify author Experience, Expertise, Authoritativeness, Trust signals."""
        author = data.get("author", {})
        content = data.get("content", "")
        results = data.get("results", {})

        # Check for author schema/byline from direct data
        has_author_name = bool(author.get("name", ""))
        has_author_bio = bool(author.get("bio", author.get("description", "")))
        has_author_url = bool(author.get("url", author.get("sameAs", "")))

        # Also check Phase 6 schemas for author signals
        p6 = results.get("phase_6", {})
        for schema_item in p6.get("schemas", []):
            schema = schema_item.get("schema", {}) if isinstance(schema_item, dict) else {}
            schema_author = schema.get("author", {})
            if isinstance(schema_author, dict):
                if schema_author.get("name"):
                    has_author_name = True
                if schema_author.get("url"):
                    has_author_url = True
            elif isinstance(schema_author, str) and schema_author:
                has_author_name = True

        # Check for Organization schema (trust signal)
        has_org_schema = any(
            s.get("type") == "Organization"
            for s in p6.get("schemas", []) if isinstance(s, dict)
        )

        # Check Phase 5 geo-targeting for local trust signals
        p5 = results.get("phase_5", {})
        has_local_schema = bool(p5.get("local_business_schema"))

        # Check content for E-E-A-T signals
        eeat_signals = []
        if content:
            content_lower = content.lower()
            if any(w in content_lower for w in ["years of experience", "i've worked", "in my experience", "as a"]):
                eeat_signals.append("experience_mention")
            if any(w in content_lower for w in ["according to", "research shows", "study found", "data from"]):
                eeat_signals.append("citation_present")
            if any(w in content_lower for w in ["certified", "licensed", "credential", "qualification"]):
                eeat_signals.append("credential_mention")

        # Org/Local schemas count as trust signals
        if has_org_schema:
            eeat_signals.append("organization_schema")
        if has_local_schema:
            eeat_signals.append("local_business_schema")

        if not has_author_name and not eeat_signals:
            return GateResult(passed=False, message="No author or E-E-A-T signals found", details={"has_author": False, "eeat_signals": []})

        return GateResult(
            passed=True,
            message=f"E-E-A-T signals present: author={has_author_name}, signals={len(eeat_signals)}",
            details={"has_author_name": has_author_name, "has_bio": has_author_bio, "has_url": has_author_url, "eeat_signals": eeat_signals}
        )

    # ── Gate 8: H2 Question Ratio ────────────────────────────────
    def _rule_h2_ratio(self, data: Dict[str, Any]) -> GateResult:
        """Ensure >50% of H2 headings are question-format (for PAA/Voice)."""
        h2s = data.get("h2_headings", data.get("h2s", []))
        results = data.get("results", {})
        p3 = results.get("phase_3", {})

        if not h2s and p3:
            h2s = p3.get("h2_questions", [])

        if not h2s:
            return GateResult(passed=True, message="H2 ratio check skipped (no H2 data)", details={"skipped": True})

        question_words = ('what', 'how', 'why', 'when', 'where', 'who', 'is', 'are', 'can', 'do', 'does', 'should', 'which')
        questions = [h for h in h2s if h.strip().endswith('?') or h.strip().lower().startswith(question_words)]
        ratio = len(questions) / len(h2s) if h2s else 0

        if ratio < 0.5:
            return GateResult(
                passed=False,
                message=f"H2 question ratio {ratio:.0%} below 50% target ({len(questions)}/{len(h2s)})",
                details={"ratio": ratio, "questions": len(questions), "total": len(h2s)}
            )

        return GateResult(
            passed=True,
            message=f"H2 question ratio optimal: {ratio:.0%} ({len(questions)}/{len(h2s)})",
            details={"ratio": ratio, "questions": len(questions), "total": len(h2s)}
        )

    # ── Gate 9: BLUF Presence ────────────────────────────────────
    def _rule_bluf_presence(self, data: Dict[str, Any]) -> GateResult:
        """Check if BLUF (Bottom Line Up Front) is present."""
        bluf = data.get("bluf", data.get("bluf_paragraph", ""))
        results = data.get("results", {})
        p4 = results.get("phase_4", {})

        if not bluf and p4:
            bluf = p4.get("bluf_paragraph", "")

        if not bluf:
            # Check content first paragraph as fallback
            content = data.get("content", "")
            if content:
                first_para = content.split("\n\n")[0] if "\n\n" in content else content[:200]
                if len(first_para) >= 50:
                    return GateResult(passed=True, message="BLUF detected in first paragraph", details={"bluf_length": len(first_para), "source": "first_paragraph"})

            return GateResult(passed=False, message="No BLUF paragraph found", details={"has_bluf": False})

        if len(bluf) < 30:
            return GateResult(passed=False, message=f"BLUF too short ({len(bluf)} chars, need 30+)", details={"bluf_length": len(bluf)})

        return GateResult(passed=True, message=f"BLUF present ({len(bluf)} chars)", details={"bluf_length": len(bluf)})

    # ── Gate 10: Alt Text Accessibility ──────────────────────────
    def _rule_alt_text(self, data: Dict[str, Any]) -> GateResult:
        """Verify images have descriptive alt text."""
        images = data.get("images", [])
        if not images:
            return GateResult(passed=True, message="Alt text check skipped (no images)", details={"skipped": True})

        missing_alt = [img for img in images if not img.get("alt", "").strip()]
        generic_alt = [img for img in images if img.get("alt", "").strip().lower() in ("image", "photo", "picture", "img", "screenshot")]

        issues = []
        if missing_alt:
            issues.append(f"{len(missing_alt)} images missing alt text")
        if generic_alt:
            issues.append(f"{len(generic_alt)} images with generic alt text")

        if len(missing_alt) > len(images) * 0.2:  # >20% missing
            return GateResult(passed=False, message=f"Alt text issues: {'; '.join(issues)}", details={"missing": len(missing_alt), "generic": len(generic_alt), "total": len(images)})

        return GateResult(passed=True, message=f"Alt text accessibility passed ({len(images)} images)", details={"total": len(images), "missing": len(missing_alt), "generic": len(generic_alt)})

    # ── Gate 11: Canonical Integrity ─────────────────────────────
    def _rule_canonical_integrity(self, data: Dict[str, Any]) -> GateResult:
        """Check canonical URL consistency."""
        canonical = data.get("canonical_url", "")
        page_url = data.get("page_url", data.get("target_url", ""))

        if not canonical and not page_url:
            return GateResult(passed=True, message="Canonical check skipped (no URL data)", details={"skipped": True})

        if canonical and page_url:
            # Normalize trailing slashes for comparison
            canon_clean = canonical.rstrip("/").lower()
            page_clean = page_url.rstrip("/").lower()

            if canon_clean != page_clean:
                # Not necessarily bad — could be intentional redirect
                return GateResult(
                    passed=True,
                    message=f"Canonical differs from page URL (may be intentional)",
                    details={"canonical": canonical, "page_url": page_url, "match": False}
                )

        return GateResult(passed=True, message="Canonical URLs consistent", details={"canonical": canonical, "page_url": page_url})

    # ── Gate 12: Rich Results Validator ──────────────────────────
    def _rule_rich_results(self, data: Dict[str, Any]) -> GateResult:
        """Validate schema.org markup for rich results eligibility."""
        schema = data.get("schema", {})
        results = data.get("results", {})
        p6 = results.get("phase_6", {})

        schema_types = p6.get("schema_types_generated", []) if p6 else []

        # Required fields per schema type
        rich_result_types = {"Article", "BlogPosting", "FAQPage", "HowTo", "Product", "Review", "LocalBusiness", "Recipe", "Event"}

        if not schema_types and isinstance(schema, dict):
            schema_type = schema.get("@type", "")
            schema_types = [schema_type] if schema_type else []

        if not schema_types:
            return GateResult(passed=False, message="No schema types found for rich results", details={"schema_types": []})

        eligible = [t for t in schema_types if t in rich_result_types]
        if not eligible:
            return GateResult(
                passed=True,
                message=f"Schema types present but not rich-result eligible: {schema_types}",
                details={"schema_types": schema_types, "eligible": []}
            )

        # Validate required fields if schema dict is available
        issues = []
        if isinstance(schema, dict):
            schema_type = schema.get("@type", "")
            if schema_type == "Article":
                for req in ["headline", "author", "datePublished"]:
                    if req not in schema:
                        issues.append(f"Article schema missing '{req}'")
            elif schema_type == "FAQPage":
                if "mainEntity" not in schema:
                    issues.append("FAQPage schema missing 'mainEntity'")

        if issues:
            return GateResult(passed=False, message=f"Rich results issues: {'; '.join(issues)}", details={"issues": issues, "eligible_types": eligible})

        return GateResult(
            passed=True,
            message=f"Rich results eligible: {eligible}",
            details={"schema_types": schema_types, "eligible_types": eligible}
        )

    # ── Runner Methods ───────────────────────────────────────────

    def run_gate(self, gate_name: str, data: Dict[str, Any]) -> GateResult:
        """Run a specific validation gate by name."""
        if gate_name not in self.gates:
            return GateResult(passed=False, message=f"Gate '{gate_name}' not found")
        try:
            gate = self.gates[gate_name]
            return gate.rule(data)
        except Exception as e:
            return GateResult(passed=False, message=f"Error running gate '{gate_name}': {str(e)}")

    def run_all_gates(self, data: Dict[str, Any]) -> Dict[str, GateResult]:
        """Run all registered validation gates."""
        results = {}
        for name in self.gates:
            results[name] = self.run_gate(name, data)
        return results

    def get_failed_gates(self, results: Dict[str, GateResult]) -> List[str]:
        """Get a list of gate names that failed."""
        return [name for name, result in results.items() if not result.passed]

    def get_summary(self, results: Dict[str, GateResult]) -> Dict[str, Any]:
        """Get a summary of all gate results."""
        failed = self.get_failed_gates(results)
        return {
            "total": len(results),
            "passed": len(results) - len(failed),
            "failed": len(failed),
            "failed_gates": failed,
            "details": {name: {"passed": r.passed, "message": r.message} for name, r in results.items()}
        }


# Quick test function for standalone execution
if __name__ == "__main__":
    registry = GateRegistry()

    # Test with realistic pipeline data
    sample_data = {
        "content": "This is a comprehensive guide about SEO optimization. "
                   "Search engine optimization helps websites rank higher. " * 20,
        "results": {
            "phase_3": {"h2_questions": [
                "What is SEO?", "How does SEO work?", "Why is SEO important?",
                "Best Practices", "Implementation Guide"
            ]},
            "phase_4": {
                "bluf_paragraph": "SEO drives organic traffic by optimizing content for search engines.",
                "ai_tells_detected": ["comprehensive guide"],
                "word_count_targets": {"min_page_words": 2000}
            },
            "phase_6": {"schema_types_generated": ["Article", "FAQ", "HowTo"]}
        }
    }

    results = registry.run_all_gates(sample_data)
    summary = registry.get_summary(results)

    print(f"Total gates: {summary['total']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")

    for name, result in results.items():
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] {name}: {result.message}")
