"""XML Sitemap Generator for SEO."""

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Optional

class SitemapGenerator:
    """Generates XML sitemaps."""
    
    XMLNS = "http://www.sitemaps.org/schemas/sitemap/0.9"

    @classmethod
    def generate(cls, urls: List[Dict[str, str]]) -> str:
        """Generate XML sitemap.
        
        Args:
            urls: List of dicts with keys: loc, lastmod (optional), changefreq (optional), priority (optional)
        
        Returns:
            String containing the XML sitemap.
        """
        ET.register_namespace('', cls.XMLNS)
        urlset = ET.Element(f"{{{cls.XMLNS}}}urlset")
        
        for url_data in urls:
            url_element = ET.SubElement(urlset, f"{{{cls.XMLNS}}}url")
            
            loc = ET.SubElement(url_element, f"{{{cls.XMLNS}}}loc")
            loc.text = url_data.get("loc", "")
            
            if "lastmod" in url_data:
                lastmod = ET.SubElement(url_element, f"{{{cls.XMLNS}}}lastmod")
                lastmod.text = url_data["lastmod"]
                
            if "changefreq" in url_data:
                changefreq = ET.SubElement(url_element, f"{{{cls.XMLNS}}}changefreq")
                changefreq.text = url_data["changefreq"]
                
            if "priority" in url_data:
                priority = ET.SubElement(url_element, f"{{{cls.XMLNS}}}priority")
                priority.text = str(url_data["priority"])
                
        # Use xml declaration and utf-8 encoding
        xml_bytes = ET.tostring(urlset, encoding='utf-8', method='xml')
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes.decode('utf-8')
