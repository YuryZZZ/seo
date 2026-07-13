"""Internal Linking Engine for SEO/GEO Framework.

Provides intelligent internal link suggestions based on keyword matching,
semantic relevance, and anchor text optimization. Generates link opportunities
that improve site architecture and distribute page authority.
"""

from __future__ import annotations

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


class LinkOpportunity:
    """Represents a single internal linking opportunity."""
    
    __slots__ = ("source_url", "target_url", "target_title", "anchor_text",
                 "relevance_score", "position", "context")
    
    def __init__(
        self,
        source_url: str,
        target_url: str,
        target_title: str,
        anchor_text: str,
        relevance_score: float = 0.0,
        position: str = "body",
        context: str = "",
    ):
        self.source_url = source_url
        self.target_url = target_url
        self.target_title = target_title
        self.anchor_text = anchor_text
        self.relevance_score = relevance_score
        self.position = position
        self.context = context
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_url": self.source_url,
            "target_url": self.target_url,
            "target_title": self.target_title,
            "anchor_text": self.anchor_text,
            "relevance_score": round(self.relevance_score, 3),
            "position": self.position,
            "context": self.context,
        }


class InternalLinker:
    """Intelligent internal linking engine.
    
    Features:
    - Keyword-based link matching
    - Relevance scoring with TF weighting
    - Anchor text optimization
    - Maximum links per page enforcement
    - Duplicate link prevention
    """
    
    def __init__(
        self,
        max_links_per_page: int = 10,
        min_relevance_score: float = 0.1,
    ):
        self.max_links_per_page = max_links_per_page
        self.min_relevance_score = min_relevance_score
    
    def suggest_links(
        self,
        current_content: str,
        all_articles: List[Dict[str, object]],
        current_url: str = "",
    ) -> List[Dict[str, str]]:
        """Suggest internal links for the given content.
        
        Args:
            current_content: The content to find link opportunities in
            all_articles: List of articles with 'title', 'url', 'keywords' keys
            current_url: URL of the current page (to avoid self-linking)
            
        Returns:
            List of link suggestion dicts with 'title', 'url', 'anchor_text', 'score'
        """
        if not current_content or not all_articles:
            return []
        
        current_lower = current_content.lower()
        opportunities: List[LinkOpportunity] = []
        seen_urls: set = set()
        
        try:
            from .ml.vector_search import VectorSearchEngine
        except ImportError:
            from ml.vector_search import VectorSearchEngine
        import numpy as np

        engine = VectorSearchEngine()

        for article in all_articles:
            target_url = str(article.get("url", ""))
            target_title = str(article.get("title", ""))
            
            # Skip self-links and duplicates
            if target_url == current_url or target_url in seen_urls:
                continue
            
            keywords = [str(k).lower() for k in article.get("keywords", [])]
            
            # Calculate relevance score (TF-IDF/heuristic basis)
            score, best_anchor = self._calculate_relevance(
                current_lower, keywords, target_title.lower()
            )
            
            # Calculate vector score (semantic basis)
            vector_score = 0.0
            try:
                target_text = f"{target_title} " + " ".join(keywords)
                embeddings = engine.generate_embeddings([current_content, target_text])
                vector_score = float(np.dot(embeddings[0], embeddings[1]))
            except Exception as e:
                logger.warning(f"Vector similarity computation failed: {e}")

            # Hybrid score (50% keyword matching, 50% semantic vector matching)
            hybrid_score = 0.5 * score + 0.5 * max(0.0, vector_score)

            if hybrid_score >= self.min_relevance_score:
                opportunities.append(LinkOpportunity(
                    source_url=current_url,
                    target_url=target_url,
                    target_title=target_title,
                    anchor_text=best_anchor or target_title,
                    relevance_score=hybrid_score,
                ))
                seen_urls.add(target_url)
        
        # Sort by relevance and limit
        opportunities.sort(key=lambda x: x.relevance_score, reverse=True)
        top = opportunities[:self.max_links_per_page]
        
        return [
            {
                "title": op.target_title,
                "url": op.target_url,
                "anchor_text": op.anchor_text,
                "score": round(op.relevance_score, 3),
            }
            for op in top
        ]
    
    def _calculate_relevance(
        self,
        content: str,
        keywords: List[str],
        title: str,
    ) -> Tuple[float, str]:
        """Calculate relevance score between content and target article.
        
        Returns:
            (score, best_anchor_text) tuple
        """
        if not keywords:
            # Fall back to title matching
            if title and title in content:
                return (0.3, title)
            return (0.0, "")
        
        total_score = 0.0
        best_anchor = ""
        best_score = 0.0
        
        for keyword in keywords:
            if not keyword:
                continue
            
            # Count occurrences (term frequency)
            count = content.count(keyword)
            if count == 0:
                continue
            
            # Score based on TF (diminishing returns)
            keyword_score = min(1.0, count * 0.2)
            
            # Bonus for longer keyword matches (more specific = more relevant)
            length_bonus = min(0.3, len(keyword.split()) * 0.1)
            keyword_score += length_bonus
            
            # Bonus if keyword appears in first 500 chars (topical relevance)
            if keyword in content[:500]:
                keyword_score += 0.15
            
            total_score += keyword_score
            
            if keyword_score > best_score:
                best_score = keyword_score
                best_anchor = keyword
        
        # Normalize score
        normalized = min(1.0, total_score / max(1, len(keywords)))
        
        return (normalized, best_anchor)
    
    def build_link_graph(
        self,
        articles: List[Dict[str, object]],
    ) -> Dict[str, List[str]]:
        """Build an internal link graph showing connections between articles.
        
        Args:
            articles: List of articles with 'url', 'content', 'keywords'
            
        Returns:
            Dict mapping source URLs to list of target URLs
        """
        graph: Dict[str, List[str]] = defaultdict(list)
        
        for article in articles:
            url = str(article.get("url", ""))
            content = str(article.get("content", ""))
            
            suggestions = self.suggest_links(content, articles, current_url=url)
            
            for suggestion in suggestions:
                graph[url].append(suggestion["url"])
        
        return dict(graph)
    
    def find_orphan_pages(
        self,
        articles: List[Dict[str, object]],
    ) -> List[str]:
        """Find pages that have no internal links pointing to them.
        
        Args:
            articles: List of articles with 'url', 'content', 'keywords'
            
        Returns:
            List of orphan page URLs
        """
        graph = self.build_link_graph(articles)
        
        all_urls = {str(a.get("url", "")) for a in articles}
        linked_urls = set()
        
        for targets in graph.values():
            linked_urls.update(targets)
        
        return sorted(all_urls - linked_urls)
