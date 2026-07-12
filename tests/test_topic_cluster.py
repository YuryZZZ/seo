"""Tests for TopicClusterer."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from topic_cluster import TopicClusterer

class TestTopicClusterer:
    
    def test_calculate_similarity(self):
        clusterer = TopicClusterer()
        sim = clusterer._calculate_similarity({"seo", "guide"}, {"seo", "tips"})
        # Intersection: {"seo"} = 1
        # Union: {"seo", "guide", "tips"} = 3
        # Similarity = 1/3 = 0.333
        assert 0.33 < sim < 0.34
        
    def test_cluster_keywords_exact_subset(self):
        clusterer = TopicClusterer()
        keywords = ["seo", "seo guide", "technical seo", "link building", "link building strategies"]
        
        clusters = clusterer.cluster_keywords(keywords)
        
        assert "seo" in clusters
        assert "seo guide" in clusters["seo"]
        assert "technical seo" in clusters["seo"]
        
        assert "link building" in clusters
        assert "link building strategies" in clusters["link building"]

    def test_cluster_keywords_similarity(self):
        clusterer = TopicClusterer(similarity_threshold=0.3)
        # "best search engine optimization tips" vs "search engine optimization guide"
        # union = 6, intersection = 3 (search, engine, optimization). sim = 0.5
        keywords = ["search engine optimization guide", "best search engine optimization tips"]
        
        clusters = clusterer.cluster_keywords(keywords)
        
        assert len(clusters) == 1
        key = list(clusters.keys())[0]
        assert len(clusters[key]) == 2
