from locust import HttpUser, task, between
import uuid

class SEOGEOFrameworkUser(HttpUser):
    """
    Simulates concurrent enterprise users hitting the SEO/GEO API endpoints
    to benchmark system throughput, concurrency limits, and latency spikes.
    """
    wait_time = between(1.0, 3.0)

    @task(10)
    def get_root(self):
        """Hit the service metadata root endpoint."""
        self.client.get("/")

    @task(8)
    def get_metrics(self):
        """Query system health, metrics, and semantic similarity gaps."""
        self.client.get("/api/v1/metrics")

    @task(5)
    def get_decay_queue(self):
        """Fetch the decaying content refresh queue."""
        self.client.get("/api/v1/decay/queue")

    @task(3)
    def create_ab_test(self):
        """Submit a new SEO A/B test case definition."""
        payload = {
            "test_id": f"locust-test-{uuid.uuid4().hex[:8]}",
            "url_pattern": "/blog/locust-load-testing-best-practices",
            "variant_a_title": "Load Testing Guide - Variant A",
            "variant_b_title": "High Throughput Load Testing - Variant B",
            "variant_a_meta": "Learn how to benchmark systems.",
            "variant_b_meta": "Discover how to optimize and load-test systems.",
            "traffic_split": 0.5
        }
        self.client.post("/api/v1/ab-test", json=payload)

    @task(2)
    def submit_job(self):
        """Post a new content generation job to the queue."""
        payload = {
            "topic": "Enterprise Kubernetes Deployments",
            "keywords": ["kubernetes", "k8s deployment", "celery redis cluster"],
            "geo_locations": ["London", "New York"]
        }
        self.client.post("/api/v1/jobs", json=payload)
