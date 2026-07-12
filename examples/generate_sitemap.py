"""Example: Generating a Sitemap."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from content_automation import SitemapGenerator

def main():
    print("Generating sitemap for example.com...")
    generator = SitemapGenerator("https://example.com")
    
    urls = [
        "https://example.com/",
        "https://example.com/about",
        "https://example.com/services",
        "https://example.com/blog",
        "https://example.com/contact"
    ]
    
    xml_content = generator.generate(urls)
    
    print("\nGenerated Sitemap:")
    print(xml_content)
    
    with open("sitemap.xml", "w") as f:
        f.write(xml_content)
    print("\nSaved to sitemap.xml")

if __name__ == "__main__":
    main()
