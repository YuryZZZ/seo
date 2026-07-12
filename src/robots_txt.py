"""Robots.txt Generator for SEO."""

from typing import List, Dict

class RobotsTxtGenerator:
    """Generates structured robots.txt files."""
    
    def __init__(self):
        self.rules: Dict[str, Dict[str, List[str]]] = {}
        self.sitemaps: List[str] = []

    def add_rule(self, user_agent: str, rule_type: str, path: str):
        """Add an allow or disallow rule for a user agent.
        
        Args:
            user_agent: The User-Agent string (e.g., '*', 'Googlebot')
            rule_type: 'Allow' or 'Disallow'
            path: The path (e.g., '/', '/admin/')
        """
        rule_type = rule_type.capitalize()
        if rule_type not in ["Allow", "Disallow"]:
            raise ValueError("rule_type must be 'Allow' or 'Disallow'")
            
        if user_agent not in self.rules:
            self.rules[user_agent] = {"Allow": [], "Disallow": []}
            
        if path not in self.rules[user_agent][rule_type]:
            self.rules[user_agent][rule_type].append(path)

    def add_sitemap(self, sitemap_url: str):
        """Add a sitemap URL to the robots.txt file."""
        if sitemap_url not in self.sitemaps:
            self.sitemaps.append(sitemap_url)

    def generate(self) -> str:
        """Generate the robots.txt content.
        
        Returns:
            String containing the formatted robots.txt content.
        """
        lines = []
        
        # User-agent rules
        # Sort so '*' is at the top, then alphabetically
        sorted_agents = sorted(self.rules.keys(), key=lambda x: (0 if x == '*' else 1, x))
        
        for idx, agent in enumerate(sorted_agents):
            if idx > 0:
                lines.append("")  # Blank line between agent blocks
            
            lines.append(f"User-agent: {agent}")
            
            # Disallow rules first
            for path in sorted(self.rules[agent]["Disallow"]):
                lines.append(f"Disallow: {path}")
                
            # Allow rules second
            for path in sorted(self.rules[agent]["Allow"]):
                lines.append(f"Allow: {path}")

        # Sitemaps
        if self.sitemaps:
            if lines:
                lines.append("")
            for sitemap in sorted(self.sitemaps):
                lines.append(f"Sitemap: {sitemap}")

        return "\n".join(lines)
