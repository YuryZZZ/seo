"""Redirect Mapping Utility for SEO."""

from typing import Dict, List, Optional, Tuple

class RedirectMapper:
    """Manages 301 and 302 redirects for SEO."""
    
    def __init__(self):
        self.redirects: Dict[str, Dict[str, Any]] = {}

    def add_redirect(self, old_url: str, new_url: str, status_code: int = 301, preserve_query: bool = True):
        """Add a redirect rule.
        
        Args:
            old_url: The source URL path
            new_url: The destination URL path
            status_code: 301 (Permanent) or 302 (Temporary)
            preserve_query: Whether to forward query strings
        """
        if status_code not in [301, 302, 307, 308]:
            raise ValueError("Status code must be 301, 302, 307, or 308")
            
        self.redirects[old_url] = {
            "target": new_url,
            "status_code": status_code,
            "preserve_query": preserve_query
        }

    def get_redirect(self, url: str) -> Optional[Tuple[str, int]]:
        """Get the redirect target and status code for a URL.
        
        Args:
            url: The requested URL
            
        Returns:
            Tuple of (target_url, status_code) or None if no redirect
        """
        # Parse query string if present
        base_url = url
        query_string = ""
        if "?" in url:
            base_url, query_string = url.split("?", 1)
            
        rule = self.redirects.get(base_url)
        if not rule:
            # Check if there's a wildcard match or regex match
            # For simplicity in this base class, we just do exact matching
            return None
            
        target = rule["target"]
        if rule["preserve_query"] and query_string:
            target += f"?{query_string}"
            
        return (target, rule["status_code"])

    def detect_redirect_loops(self) -> List[List[str]]:
        """Detect infinite redirect loops.
        
        Returns:
            List of paths involved in a loop (e.g., [['/a', '/b', '/a']])
        """
        loops = []
        for start_url in self.redirects:
            visited = []
            current = start_url
            
            while current in self.redirects:
                if current in visited:
                    # Found a loop
                    loop_path = visited[visited.index(current):]
                    # Normalize the loop to avoid duplicates (e.g. A->B->C vs B->C->A)
                    if loop_path:
                        min_idx = loop_path.index(min(loop_path))
                        normalized_loop = loop_path[min_idx:] + loop_path[:min_idx]
                        if normalized_loop not in loops:
                            loops.append(normalized_loop)
                    break
                    
                visited.append(current)
                current = self.redirects[current]["target"]
                
        return loops

    def detect_redirect_chains(self, max_length: int = 2) -> List[List[str]]:
        """Detect redirect chains longer than max_length.
        
        Long chains (A -> B -> C -> D) dilute link equity.
        
        Args:
            max_length: Maximum allowed chain length before flagging
            
        Returns:
            List of chains (e.g., [['/a', '/b', '/c', '/d']])
        """
        chains = []
        
        # Don't check paths that are just middle nodes
        all_targets = {rule["target"] for rule in self.redirects.values()}
        starts = [url for url in self.redirects if url not in all_targets]
        
        # If there's a loop, a node might not be in starts. Fallback to all.
        if not starts:
            starts = list(self.redirects.keys())
            
        for start_url in starts:
            chain = [start_url]
            current = start_url
            
            while current in self.redirects:
                target = self.redirects[current]["target"]
                
                # Prevent infinite loop
                if target in chain:
                    break
                    
                chain.append(target)
                current = target
                
            if len(chain) > max_length + 1:  # A -> B is length 2, allowed if max_length=1
                chains.append(chain)
                
        return chains

    def generate_nginx_config(self) -> str:
        """Generate Nginx rewrite rules."""
        lines = []
        for old_url, data in self.redirects.items():
            flag = "permanent" if data["status_code"] in [301, 308] else "redirect"
            lines.append(f"rewrite ^{old_url}$ {data['target']} {flag};")
        return "\n".join(lines)
