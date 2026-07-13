import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "seo_framework_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Standard configurations for enterprise production
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour limit
)

@celery_app.task(bind=True, name="run_seo_orchestrator_job")
def run_seo_orchestrator_job_task(self, topic: str, keywords: list, target_url: str):
    """
    Distributed Celery task for running the SEO GEO Orchestrator pipeline.
    """
    import asyncio
    try:
        from .orchestrator import SEOGEOOrchestrator
    except ImportError:
        from orchestrator import SEOGEOOrchestrator
        
    orchestrator = SEOGEOOrchestrator()
    payload = {
        "focus_keyword": keywords[0] if keywords else "seo",
        "target_keywords": keywords,
        "target_url": target_url,
        "topic": topic
    }
    
    # Run the async pipeline inside the event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    result = loop.run_until_complete(orchestrator.execute_full_pipeline(payload))
    return result
