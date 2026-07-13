import hashlib
import numpy as np
from typing import List, Dict, Any, Tuple, Optional

class VectorSearchEngine:
    """
    Local Vector Search and Semantic Gap Analysis Engine.
    Uses hash-deterministic embeddings (or live API if configured)
    and cosine similarity for KNN search and gap analysis.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index: List[Tuple[str, np.ndarray, Dict[str, Any]]] = []

    def _generate_word_vector(self, word: str) -> np.ndarray:
        """Generates a deterministic vector for a given word using sha256 seeding."""
        hasher = hashlib.sha256(word.encode('utf-8'))
        seed = int(hasher.hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        vec = rng.normal(0.0, 1.0, self.dimension)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generates dense vector embeddings for a list of texts.
        Uses a deterministic bag-of-words vector average as a local fallback.
        """
        embeddings = []
        for text in texts:
            words = [w.strip().lower() for w in text.split() if len(w.strip()) > 1]
            if not words:
                # Return zero vector if text is empty
                embeddings.append(list(np.zeros(self.dimension)))
                continue

            word_vectors = [self._generate_word_vector(w) for w in words]
            doc_vector = np.mean(word_vectors, axis=0)
            
            # Normalize doc vector
            norm = np.linalg.norm(doc_vector)
            if norm > 0:
                doc_vector = doc_vector / norm
            
            embeddings.append(list(doc_vector))
        return embeddings

    def add_to_index(self, doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Adds a document and its embedding vector to the local index."""
        vector = np.array(self.generate_embeddings([text])[0])
        self.index.append((doc_id, vector, metadata or {}))

    def clear_index(self) -> None:
        """Clears the current index."""
        self.index = []

    def search_knn(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Performs K-Nearest Neighbors search using cosine similarity.
        """
        if not self.index:
            return []

        query_vec = np.array(self.generate_embeddings([query])[0])
        
        results = []
        for doc_id, doc_vec, meta in self.index:
            # Cosine similarity
            similarity = float(np.dot(query_vec, doc_vec))
            results.append({
                "doc_id": doc_id,
                "score": round(similarity, 4),
                "metadata": meta
            })

        # Sort by similarity descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:k]

    def analyze_semantic_gaps(self, target_serp_texts: List[str], our_content_texts: List[str]) -> Dict[str, Any]:
        """
        Compares competitor target SERP text embeddings against our own content embeddings
        to isolate content gap topics and suggest optimizations.
        """
        if not target_serp_texts or not our_content_texts:
            return {
                "overall_similarity": 0.0,
                "semantic_gap_score": 1.0,
                "missing_semantic_topics": ["No input texts provided for comparison."]
            }

        comp_vectors = [np.array(v) for v in self.generate_embeddings(target_serp_texts)]
        our_vectors = [np.array(v) for v in self.generate_embeddings(our_content_texts)]

        # Calculate average similarity of each competitor text to our content base
        similarities = []
        for comp_vec in comp_vectors:
            best_match = 0.0
            for our_vec in our_vectors:
                sim = float(np.dot(comp_vec, our_vec))
                if sim > best_match:
                    best_match = sim
            similarities.append(best_match)

        overall_sim = float(np.mean(similarities))
        semantic_gap = round(1.0 - overall_sim, 4)

        # Identify which competitor texts have the lowest similarity to our content (potential gaps)
        gap_indices = np.argsort(similarities)
        missing_topics = []
        for idx in gap_indices[:3]:
            if idx < len(target_serp_texts):
                # Clean up / truncate suggestion
                snippet = target_serp_texts[idx].strip()
                if len(snippet) > 80:
                    snippet = snippet[:77] + "..."
                missing_topics.append(snippet)

        return {
            "overall_similarity": round(overall_sim, 4),
            "semantic_gap_score": semantic_gap,
            "missing_semantic_topics": missing_topics
        }
