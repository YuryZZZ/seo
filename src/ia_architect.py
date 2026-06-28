import json
import re
from typing import List, Dict, Any, Tuple, Optional

"""
Module: ia_architect
Purpose: Information architecture design and content structuring for SEO/GEO framework.
Key Classes:
- IAArchitect: Main information architecture class
Part of SEO/GEO Framework - 10-agent orchestration system.
"""


class IAArchitect:
    """
    Information Architecture (IA) Architect for the SEO/GEO Framework.
    Responsible for structuring content, headings, internal linking, and schemas.
    """
    def __init__(self, topic: str = "General", keyword_data: Dict[str, Any] = None):
        self.topic = topic
        self.keyword_data = keyword_data or {}

    def generate_h2_questions(
        self,
        candidate_h2s: Optional[List[str] | str],
        context: Any = None,
        count: Optional[int] = None,
    ) -> List[str]:
        """
        Ensure >50% of H2s are questions to optimize for PAA (People Also Ask) and Voice Search.
        """
        if candidate_h2s is None:
            return []
        if hasattr(candidate_h2s, 'h2_headings') or hasattr(candidate_h2s, 'h2_structure'):
            h2_struct = getattr(candidate_h2s, 'h2_headings', None) or getattr(candidate_h2s, 'h2_structure', None)
            if h2_struct:
                candidate_h2s = h2_struct
            else:
                candidate_h2s = getattr(candidate_h2s, 'focus_keyword', None) or getattr(candidate_h2s, 'post_title', '') or ''
        if isinstance(candidate_h2s, str):
            topic = candidate_h2s.strip()
            if not topic:
                return []
            requested = max(1, count or 6)
            candidate_h2s = [
                f"What is {topic}?",
                f"How does {topic} work?",
                f"Why does {topic} matter?",
                f"When should you use {topic}?",
                f"Who benefits from {topic}?",
                f"What mistakes should you avoid with {topic}?",
            ][:requested]
        question_words = ('what', 'how', 'why', 'when', 'where', 'who', 'is', 'are', 'can', 'do', 'does')
        
        questions = []
        non_questions = []
        
        for h in candidate_h2s:
            clean_h = h.strip().lower()
            if clean_h.endswith('?') or clean_h.startswith(question_words):
                questions.append(h)
            else:
                non_questions.append(h)
                
        result = list(questions)
        
        # Calculate how many questions are needed to be > 50%
        total_current = len(candidate_h2s)
        needed_questions = (total_current // 2) + 1 - len(questions)
        
        if needed_questions > 0:
            # Add topic-relevant questions
            default_questions = [
                f"What is {self.topic} and why does it matter?",
                f"How does {self.topic} work in practice?",
                f"What are the key benefits of {self.topic}?",
                f"Who can benefit most from {self.topic}?",
                f"How to get started with {self.topic}?"
            ]
            for i in range(min(needed_questions, len(default_questions))):
                result.append(default_questions[i])
                
        result.extend(non_questions)
        
        # Final safety check
        q_count = len([h for h in result if h.strip().endswith('?') or h.strip().lower().startswith(question_words)])
        if q_count / len(result) <= 0.5:
            result.append(f"Are there any alternatives to {self.topic}?")
            
        return result

    def design_citable_blocks(self, h2_list: Optional[List[str] | str], context: Any = None) -> Dict[str, Dict[str, str]] | List[Any]:
        """
        Map tables/lists to H2s to create citable snippet blocks (Snippet Bait).
        """
        if not h2_list:
            return []
        if hasattr(h2_list, 'h2_headings') or hasattr(h2_list, 'h2_structure'):
            h2_struct = getattr(h2_list, 'h2_headings', None) or getattr(h2_list, 'h2_structure', None)
            if h2_struct:
                h2_list = h2_struct
            else:
                h2_list = []
        if isinstance(h2_list, dict):
            return list(h2_list.keys())
        if isinstance(h2_list, str):
            h2_list = [h2_list]
        blocks = {}
        for i, h2 in enumerate(h2_list):
            # Alternate between table and list for variety
            block_type = "table" if i % 2 == 0 else "list"
            blocks[h2] = {
                "type": block_type,
                "target_h2": h2,
                "structure_suggestion": f"Create a concise {block_type} summarizing '{h2}' for featured snippets."
            }
        return blocks

    def build_hub_spoke_graph(self, parent_url: str, child_urls: List[str]) -> Dict[str, Any]:
        """
        Create parent/child URL mapping for Hub and Spoke cluster model.
        """
        graph = {
            "hub": parent_url,
            "spokes": child_urls,
            "internal_links": []
        }
        for child in child_urls:
            # Spoke points to Hub
            graph["internal_links"].append({
                "from_url": child,
                "to_url": parent_url,
                "rel": "hub",
                "context": "Contextual link from spoke to main pillar hub"
            })
            # Hub points to Spoke
            graph["internal_links"].append({
                "from_url": parent_url,
                "to_url": child,
                "rel": "spoke",
                "context": "Cluster index link from hub to supporting spoke"
            })
        return graph

    def create_breadcrumb_structure(self, url_path: str, site_url: str) -> str:
        """
        Generate BreadcrumbList schema (JSON-LD) for the given URL path.
        """
        parts = [p for p in url_path.strip('/').split('/') if p]
        item_list_element = []
        
        # Root/Home
        item_list_element.append({
            "@type": "ListItem",
            "position": 1,
            "name": "Home",
            "item": site_url.rstrip('/')
        })
        
        current_url = site_url.rstrip('/')
        for i, part in enumerate(parts):
            current_url = f"{current_url}/{part}"
            name = part.replace('-', ' ').title()
            item_list_element.append({
                "@type": "ListItem",
                "position": i + 2,
                "name": name,
                "item": current_url
            })
            
        schema = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": item_list_element
        }
        return json.dumps(schema, indent=2)

    def generate_table_of_contents(self, h2_list: List[str]) -> str:
        """
        Generate HTML Table of Contents with jump-link anchors.
        """
        toc_html = ["<nav class='table-of-contents' aria-label='Table of Contents'>", "  <ul>"]
        for h2 in h2_list:
            anchor = re.sub(r'[^a-z0-9]+', '-', h2.lower()).strip('-')
            toc_html.append(f"    <li><a href='#{anchor}'>{h2}</a></li>")
        toc_html.append("  </ul>")
        toc_html.append("</nav>")
        return "\\n".join(toc_html)

    def plan_anchor_text_strategy(self, target_urls: List[str], primary_keywords: List[str]) -> List[Dict[str, str]]:
        """
        Plan descriptive and varied anchors for target URLs to avoid over-optimization.
        """
        strategy = []
        for i, url in enumerate(target_urls):
            kw = primary_keywords[i % len(primary_keywords)] if primary_keywords else "click here"
            strategy.append({
                "target_url": url,
                "exact_match_anchor": kw,
                "partial_match_anchor": f"guide to {kw}",
                "descriptive_anchor": f"learn more about {kw} strategies",
                "lsi_anchor": f"related {kw} resources"
            })
        return strategy

    def set_primary_term(self, term: str, category_map: Dict[str, str]) -> Dict[str, str]:
        """
        Map the primary term to a category.
        """
        category = category_map.get(term, "Uncategorized")
        return {
            "primary_term": term,
            "mapped_category": category,
            "taxonomy_tag": term.lower().replace(' ', '-')
        }

    def set_cornerstone_content(self, is_pillar: bool) -> Dict[str, bool]:
        """
        Set the pillar page flag for cornerstone content, triggering deeper comprehensive coverage rules.
        """
        return {
            "is_cornerstone": is_pillar,
            "requires_comprehensive_coverage": is_pillar,
            "priority_indexing": is_pillar,
            "is_hub_page": is_pillar
        }

