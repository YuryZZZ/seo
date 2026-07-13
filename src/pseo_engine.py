"""
Programmatic SEO (pSEO) Data Engine for generating bulk content.

Provides CSV/JSON parsing, Jinja2 templating, and hash-deterministic spin-text.
"""

import csv
import json
import re
import hashlib
import random
from typing import Dict, List, Any, Optional
from jinja2 import Template


class PSEODataParser:
    """Parses and validates CSV/JSON datasets for programmatic page generation."""

    @staticmethod
    def parse_csv(file_path: str) -> List[Dict[str, Any]]:
        """Parses a CSV file into a list of row dictionaries."""
        rows = []
        with open(file_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Clean up keys and values (strip whitespace)
                cleaned_row = {
                    (k.strip() if k else ""): (v.strip() if v else "")
                    for k, v in row.items()
                }
                if any(cleaned_row.values()):  # Skip completely empty rows
                    rows.append(cleaned_row)
        return rows

    @staticmethod
    def parse_json(file_path: str) -> List[Dict[str, Any]]:
        """Parses a JSON file into a list of row dictionaries."""
        with open(file_path, mode="r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [
                {k: (v.strip() if isinstance(v, str) else v) for k, v in item.items()}
                for item in data if isinstance(item, dict)
            ]
        elif isinstance(data, dict):
            # If it's a single object, wrap it in a list
            return [{k: (v.strip() if isinstance(v, str) else v) for k, v in data.items()}]
        raise ValueError("Invalid JSON dataset format: Must be a list of objects or a single object.")


class SpinTextGenerator:
    """Processes spin-text templates to ensure high content uniqueness and variety."""

    SPIN_PATTERN = re.compile(r"\{([^{}]+)\}")

    @classmethod
    def spin(cls, text: str, seed: Optional[str] = None) -> str:
        """
        Resolves spin-text options, e.g. 'This is {easy|simple|fast}'.
        
        If a seed is provided, uses deterministic hashing to ensure the spun result
        remains stable for the same seed/input.
        """
        if not text:
            return ""

        # Determine seed
        local_random = random.Random()
        if seed is not None:
            # Generate a numeric seed from md5 hash
            hash_val = hashlib.md5(seed.encode("utf-8")).hexdigest()
            local_random.seed(int(hash_val, 16))

        def replace_spin(match):
            options = match.group(1).split("|")
            return local_random.choice(options).strip()

        # Resolve nested spin blocks iteratively
        spun_text = text
        while cls.SPIN_PATTERN.search(spun_text):
            spun_text = cls.SPIN_PATTERN.sub(replace_spin, spun_text)

        return spun_text


class PSEOEngine:
    """Combines Jinja2 templates, spin-text, and datasets to bulk-generate pages."""

    def __init__(
        self,
        title_template: str,
        meta_desc_template: str,
        h1_template: str,
        body_template: str,
    ):
        self.title_tmpl = Template(title_template)
        self.meta_tmpl = Template(meta_desc_template)
        self.h1_tmpl = Template(h1_template)
        self.body_tmpl = Template(body_template)

    def render_page(self, row_data: Dict[str, Any], spin: bool = True, seed_key: Optional[str] = None) -> Dict[str, str]:
        """Renders a single page using the provided row data."""
        # 1. First-pass Jinja2 rendering to inject fields
        title = self.title_tmpl.render(**row_data)
        meta_desc = self.meta_tmpl.render(**row_data)
        h1 = self.h1_tmpl.render(**row_data)
        body = self.body_tmpl.render(**row_data)

        # 2. Second-pass synonym spinning
        if spin:
            # Seed value based on the seed_key or title if seed_key is not in row_data
            seed_val = None
            if seed_key and seed_key in row_data:
                seed_val = str(row_data[seed_key])
            elif "slug" in row_data:
                seed_val = str(row_data["slug"])
            elif "title" in row_data:
                seed_val = str(row_data["title"])

            title = SpinTextGenerator.spin(title, seed_val)
            meta_desc = SpinTextGenerator.spin(meta_desc, seed_val)
            h1 = SpinTextGenerator.spin(h1, seed_val)
            body = SpinTextGenerator.spin(body, seed_val)

        return {
            "title": title,
            "meta_description": meta_desc,
            "h1": h1,
            "body": body,
        }

    def bulk_render(
        self,
        dataset: List[Dict[str, Any]],
        spin: bool = True,
        seed_key: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Renders a collection of pages in batch."""
        results = []
        for index, row in enumerate(dataset):
            rendered = self.render_page(row, spin=spin, seed_key=seed_key)
            # Retain original row data for context
            item = {
                "row_index": index,
                "data": row,
                "rendered": rendered,
            }
            results.append(item)
        return results
