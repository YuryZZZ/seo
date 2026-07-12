"""Local SEO and Internationalization module."""

from typing import Dict, Any, List
import copy

class LocalSEOManager:
    """Manages local SEO logic including multi-location schema."""
    
    @staticmethod
    def generate_multi_location_schema(base_organization: Dict[str, Any], locations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate schema for an organization with multiple locations.
        
        Args:
            base_organization: The main Organization schema.
            locations: List of location dictionaries with 'name', 'address', 'telephone'.
            
        Returns:
            Organization schema augmented with departments/locations.
        """
        schema = copy.deepcopy(base_organization)
        if "@type" not in schema:
            schema["@type"] = "Organization"
            
        schema["department"] = []
        for loc in locations:
            department = {
                "@type": "LocalBusiness",
                "name": loc.get("name", schema.get("name", "Branch")),
                "address": loc.get("address"),
                "telephone": loc.get("telephone")
            }
            if "url" in loc:
                department["url"] = loc["url"]
            schema["department"].append(department)
            
        return schema
        
    @staticmethod
    def generate_geo_keyword_variations(base_keyword: str, locations: List[str]) -> List[str]:
        """Generate geo-targeted variations for a keyword.
        
        Args:
            base_keyword: The base keyword (e.g., 'plumber').
            locations: List of locations (e.g., ['London', 'Manchester']).
            
        Returns:
            List of localized keywords.
        """
        variations = []
        for loc in locations:
            variations.extend([
                f"{base_keyword} in {loc}",
                f"{loc} {base_keyword}",
                f"best {base_keyword} {loc}"
            ])
        return variations

class InternationalizationManager:
    """Manages international SEO logic."""
    
    @staticmethod
    def generate_hreflang_tags(current_url: str, alternates: Dict[str, str]) -> str:
        """Generate hreflang link tags.
        
        Args:
            current_url: The URL of the current page.
            alternates: Dictionary mapping language code to alternate URL (e.g., {'fr': 'https://example.com/fr'}).
            
        Returns:
            HTML string containing link tags.
        """
        tags = []
        # Include self-referencing x-default if appropriate or just the alternates
        for lang, url in alternates.items():
            tags.append(f'<link rel="alternate" hreflang="{lang}" href="{url}" />')
            
        return "\n".join(tags)
        
    @staticmethod
    def add_multilingual_sitemap_entries(sitemap_urls: List[Dict[str, Any]]) -> str:
        """Generate an XML sitemap supporting hreflang alternates.
        
        Args:
            sitemap_urls: List of dicts, each with 'loc' and optionally 'alternates'.
                          alternates is a dict of {lang: url}.
                          
        Returns:
            XML string for sitemap.
        """
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
            '        xmlns:xhtml="http://www.w3.org/1999/xhtml">'
        ]
        
        for item in sitemap_urls:
            lines.append('  <url>')
            lines.append(f'    <loc>{item["loc"]}</loc>')
            
            if "alternates" in item:
                for lang, alt_url in item["alternates"].items():
                    lines.append(f'    <xhtml:link rel="alternate" hreflang="{lang}" href="{alt_url}"/>')
                    
            lines.append('  </url>')
            
        lines.append('</urlset>')
        return "\n".join(lines)
        
    @staticmethod
    def translate_with_seo_context(content: str, target_language: str, target_keyword: str) -> str:
        """Placeholder for GenAI-based translation with SEO awareness.
        
        In a real implementation, this would call the LLMClient with a specific prompt.
        """
        # Placeholder behavior
        return f"[Translated to {target_language} focusing on '{target_keyword}']: {content}"
