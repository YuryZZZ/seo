"""Topic Clustering module for SEO Hub architecture."""

from typing import List, Dict, Any, Set
from collections import defaultdict

class TopicClusterer:
    """Groups keywords and pages into semantic clusters for pillar/cluster SEO architectures."""
    
    def __init__(self, similarity_threshold: float = 0.3):
        self.similarity_threshold = similarity_threshold

    def _calculate_similarity(self, words1: Set[str], words2: Set[str]) -> float:
        """Calculate Jaccard similarity between two sets of words."""
        if not words1 and not words2:
            return 0.0
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        return intersection / union if union > 0 else 0.0

    def cluster_keywords(self, keywords: List[str]) -> Dict[str, List[str]]:
        """Cluster a list of keywords based on word overlap.
        
        Args:
            keywords: List of keyword strings.
            
        Returns:
            Dict mapping pillar/parent keywords to lists of related keywords.
        """
        # Clean and tokenize
        tokenized = {}
        for kw in keywords:
            words = set(kw.lower().split())
            tokenized[kw] = words
            
        # Sort by length (shortest often make best pillar topics)
        sorted_keywords = sorted(keywords, key=lambda x: len(x.split()))
        
        clusters = defaultdict(list)
        assigned = set()
        
        for parent in sorted_keywords:
            if parent in assigned:
                continue
                
            parent_words = tokenized[parent]
            clusters[parent].append(parent)
            assigned.add(parent)
            
            for child in sorted_keywords:
                if child in assigned:
                    continue
                    
                child_words = tokenized[child]
                
                # Check if child contains all parent words (direct subset)
                is_subset = parent_words.issubset(child_words)
                
                # Or check overall similarity
                similarity = self._calculate_similarity(parent_words, child_words)
                
                if is_subset or similarity >= self.similarity_threshold:
                    clusters[parent].append(child)
                    assigned.add(child)
                    
        return dict(clusters)
