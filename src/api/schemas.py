from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from uuid import UUID

class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    version: str
    timestamp: datetime

class JobSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str = Field(min_length=5, max_length=500, description="Content topic")
    keywords: List[str] = Field(max_length=20, description="Target keywords")
    content_type: Literal["blog", "landing_page", "product_page", "faq"]
    target_audience: Optional[str] = Field(default=None, max_length=200)
    tone: Literal["professional", "casual", "technical", "persuasive"] = "professional"
    priority: int = Field(ge=1, le=5, default=3)

class RowPayloadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    post_id: int
    post_title: str
    post_content: str
    post_excerpt: Optional[str] = None
    seo_title: str
    meta_description: str
    focus_keyword: str
    canonical_url: str
    url_slug: str
    schema_type: str
    schema_markup: Optional[str] = None
    serp_snapshot_raw: Optional[str] = None
    paa_extraction: Optional[List[str]] = None
    competitor_missing_gaps: Optional[List[str]] = None
    bluf_paragraph: Optional[str] = None
    snippet_bait_block: Optional[str] = None
    ai_tell_score: Optional[float] = None

class JobResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: UUID
    status: Literal["pending", "running", "completed", "failed"]
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[RowPayloadResponse] = None
    error_message: Optional[str] = None

class AgentStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_name: str
    is_available: bool
    last_run: Optional[datetime] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)

class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error_code: str
    message: str
    details: Optional[List[Dict[str, Any]]] = None
    timestamp: datetime

class JobListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jobs: List[JobResponse]
    total: int
    offset: int
    limit: int


class SEOFrameworkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str = Field(min_length=3, max_length=200, description="Seed topic for the framework")
    base_url: str = Field(default="https://example.com")
    target_keyword_count: int = Field(default=600, ge=100, le=5000)
    target_topic_count: int = Field(default=48, ge=12, le=500)
    max_spokes_per_cluster: int = Field(default=6, ge=2, le=12)
    max_repository_terms: int = Field(default=800, ge=200, le=5000)
    enable_live: bool = True
    write_artifacts: bool = True
    output_json: Optional[str] = None
    output_md: Optional[str] = None
    include_framework: bool = False


class SEOFrameworkResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    topic: str
    framework_type: str
    keywords: int
    topics: int
    app_pages: int
    templates: int
    flows: int
    output_json: Optional[str] = None
    output_md: Optional[str] = None
    framework: Optional[Dict[str, Any]] = None


class SEODraftsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str = Field(min_length=3, max_length=200)
    base_url: str = Field(default="https://example.com")
    package_json: Optional[str] = None
    output_root: Optional[str] = None
    enable_live: bool = True


class SEODraftsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    topic: str
    draft_count: int
    flow_count: int
    output_root: str


class PSEOPageTemplates(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title_template: str
    meta_description_template: str
    h1_template: str
    body_template: str


class PSEOBulkGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    templates: PSEOPageTemplates
    dataset: List[Dict[str, Any]]
    spin: bool = True
    seed_key: Optional[str] = None


class PSEORenderedPage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    meta_description: str
    h1: str
    body: str


class PSEORenderedRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    row_index: int
    data: Dict[str, Any]
    rendered: PSEORenderedPage


class PSEOBulkGenerateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    pages: List[PSEORenderedRow]
