import pytest
import numpy as np
import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ml.vector_search import VectorSearchEngine
from src.internal_linker import InternalLinker
from src.api.main import app

client = TestClient(app)


class TestVectorSemanticGaps:
    """Tests the vector search, semantic gap analysis, and hybrid linking engine."""

    def test_embeddings_generation(self):
        engine = VectorSearchEngine(dimension=128)
        
        # Test basic generation
        texts = ["Cloud SQL setup", "AlloyDB deployment tutorial", "Container clusters GKE"]
        embeddings = engine.generate_embeddings(texts)
        
        assert len(embeddings) == 3
        assert len(embeddings[0]) == 128
        
        # Test L2-normalization
        norm = np.linalg.norm(embeddings[0])
        assert pytest.approx(norm, abs=1e-5) == 1.0
        
        # Test empty text handling
        empty = engine.generate_embeddings([""])
        assert len(empty) == 1
        assert np.linalg.norm(empty[0]) == 0.0

        # Test determinism
        emb_1 = engine.generate_embeddings(["Spanner database guide"])
        emb_2 = engine.generate_embeddings(["Spanner database guide"])
        assert np.allclose(emb_1, emb_2)

    def test_knn_search(self):
        engine = VectorSearchEngine(dimension=128)
        
        # Index documents
        engine.add_to_index("doc_sql", "We will show you how to configure Google Cloud SQL for high availability.")
        engine.add_to_index("doc_alloydb", "AlloyDB Omni provides high-performance PostgreSQL compatible engines inside containers.")
        engine.add_to_index("doc_gke", "Deploying microservices to Google Kubernetes Engine clusters using helm charts.")
        
        # Search GKE related query
        results = engine.search_knn("kubernetes cluster deploy", k=2)
        
        assert len(results) == 2
        assert results[0]["doc_id"] == "doc_gke"
        assert results[0]["score"] > results[1]["score"]

    def test_semantic_gaps_analysis(self):
        engine = VectorSearchEngine(dimension=128)
        
        competitor_snippets = [
            "AlloyDB is a fully managed PostgreSQL compatible database service.",
            "Set up high availability and replication in Cloud SQL.",
            "Deploy Kubernetes clusters using Google Cloud GKE console."
        ]
        
        our_content = [
            "Setting up high availability on Cloud SQL database instances."
        ]
        
        gaps = engine.analyze_semantic_gaps(competitor_snippets, our_content)
        
        assert "overall_similarity" in gaps
        assert "semantic_gap_score" in gaps
        assert "missing_semantic_topics" in gaps
        
        # The competitor snippet most similar to our content should have highest similarity,
        # and the most different one (GKE/AlloyDB) should be recommended as missing topic.
        assert len(gaps["missing_semantic_topics"]) > 0

    def test_hybrid_internal_linker(self):
        linker = InternalLinker(max_links_per_page=5, min_relevance_score=0.1)
        
        current_content = "To store data, we recommend using Cloud SQL PostgreSQL or MySQL instances."
        all_articles = [
            {"title": "Configuring Cloud SQL", "url": "https://example.com/cloud-sql", "keywords": ["cloud sql", "mysql", "postgresql"]},
            {"title": "Setting up Kubernetes", "url": "https://example.com/k8s", "keywords": ["kubernetes", "gke"]}
        ]
        
        suggestions = linker.suggest_links(
            current_content=current_content,
            all_articles=all_articles,
            current_url="https://example.com/home"
        )
        
        # Cloud SQL should be suggested and have a high hybrid score
        assert len(suggestions) > 0
        assert suggestions[0]["title"] == "Configuring Cloud SQL"

    def test_metrics_api_endpoint(self):
        # Request semantic gap analysis on /api/v1/metrics
        response = client.get(
            "/api/v1/metrics",
            params={
                "target": "Deploy containerized AlloyDB Omni databases on GKE.",
                "reference": [
                    "How to run AlloyDB databases.",
                    "Kubernetes container deployment best practices."
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "semantic_similarity" in data
        sim_data = data["semantic_similarity"]
        assert "semantic_gap_score" in sim_data
        assert "overall_similarity" in sim_data
        assert len(sim_data["missing_semantic_topics"]) > 0
