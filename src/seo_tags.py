"""SEO Meta Tags Generator."""

from typing import Dict, List, Optional

class SEOTagGenerator:
    """Generates HTML meta tags for SEO."""
    
    @staticmethod
    def generate_canonical_tag(url: str) -> str:
        """Generate a canonical link tag.
        
        Args:
            url: The canonical URL
            
        Returns:
            HTML link tag string
        """
        if not url:
            return ""
        return f'<link rel="canonical" href="{url}" />'

    @staticmethod
    def generate_open_graph_tags(
        title: str,
        type: str = "website",
        url: str = "",
        image: str = "",
        description: str = "",
        site_name: str = "",
        locale: str = "en_US"
    ) -> str:
        """Generate Open Graph meta tags.
        
        Args:
            title: og:title
            type: og:type (e.g., website, article)
            url: og:url
            image: og:image
            description: og:description
            site_name: og:site_name
            locale: og:locale
            
        Returns:
            HTML string with meta tags separated by newlines
        """
        tags = [
            f'<meta property="og:title" content="{title}" />',
            f'<meta property="og:type" content="{type}" />',
            f'<meta property="og:locale" content="{locale}" />'
        ]
        
        if url:
            tags.append(f'<meta property="og:url" content="{url}" />')
        if image:
            tags.append(f'<meta property="og:image" content="{image}" />')
        if description:
            # Escape quotes
            clean_desc = description.replace('"', '&quot;')
            tags.append(f'<meta property="og:description" content="{clean_desc}" />')
        if site_name:
            tags.append(f'<meta property="og:site_name" content="{site_name}" />')
            
        return "\n".join(tags)

    @staticmethod
    def generate_twitter_card_tags(
        card_type: str = "summary_large_image",
        title: str = "",
        description: str = "",
        image: str = "",
        site: str = "",
        creator: str = ""
    ) -> str:
        """Generate Twitter Card meta tags.
        
        Args:
            card_type: twitter:card (e.g., summary, summary_large_image)
            title: twitter:title
            description: twitter:description
            image: twitter:image
            site: twitter:site (@username)
            creator: twitter:creator (@username)
            
        Returns:
            HTML string with meta tags separated by newlines
        """
        tags = [
            f'<meta name="twitter:card" content="{card_type}" />'
        ]
        
        if title:
            tags.append(f'<meta name="twitter:title" content="{title}" />')
        if description:
            clean_desc = description.replace('"', '&quot;')
            tags.append(f'<meta name="twitter:description" content="{clean_desc}" />')
        if image:
            tags.append(f'<meta name="twitter:image" content="{image}" />')
        if site:
            tags.append(f'<meta name="twitter:site" content="{site}" />')
        if creator:
            tags.append(f'<meta name="twitter:creator" content="{creator}" />')
            
        return "\n".join(tags)
