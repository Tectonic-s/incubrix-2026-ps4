"""Data models for connectors and connector contract."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Rendition(BaseModel):
    title: str
    body: str
    media_urls: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    canonical_url: Optional[str] = None
    is_promotional: bool = False
    has_ai_disclosure: bool = False
    extra_meta: Dict[str, Any] = Field(default_factory=dict)


class Connection(BaseModel):
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    token: Optional[str] = None
    username: Optional[str] = None
    webhook_secret: Optional[str] = None
    extra_headers: Dict[str, str] = Field(default_factory=dict)


class Destination(BaseModel):
    id: Optional[str] = None
    name: str
    url: str
    platform_key: str
    surface: str = "topic"
    category: str = "general"
    audience_tags: List[str] = Field(default_factory=list)
    language: str = "en"
    geo: str = "global"
    est_audience: int = 1000
    rules_url: Optional[str] = None
    frequency_cap: str = "1/7d"  # e.g., 1 post per 7 days
    self_promo_allowed: bool = True
    link_policy: str = "allowed"  # allowed, no_affiliate, banned, first_comment
    disclosure_required: bool = False
    automation_allowed: bool = True
    connector_key: str
    relevance_score: int = Field(default=3, ge=1, le=5)
    relevance_reason: str = ""
    level: str = "L0"  # L0, L1, L2, L3, L4
    last_certified_at: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)


# Connector Contract Responses
class ValidateResponse(BaseModel):
    ok: bool
    violations: List[str] = Field(default_factory=list)


class PublishResponse(BaseModel):
    platform_post_id: str
    live_url: str
    status: str = "published"


class StatusResponse(BaseModel):
    status: str
    live_url: str


class DeleteResponse(BaseModel):
    deleted: bool


class MetricsResponse(BaseModel):
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    watch_time_s: int = 0
    clicks: int = 0


class RefreshAuthResponse(BaseModel):
    expires_at: str


class AssistPackResponse(BaseModel):
    files: List[str] = Field(default_factory=list)
    caption: str
    deep_link: str
    checklist: List[str] = Field(default_factory=list)


# Standard Error Models (Integration Standard 5)
class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# Request bodies for POST /connector/v1/{connector_key}/{method}
class ValidateRequest(BaseModel):
    rendition: Rendition
    destination: Destination
    connection: Connection


class PublishRequest(BaseModel):
    rendition: Rendition
    destination: Destination
    connection: Connection
    idempotency_key: Optional[str] = None


class GetStatusRequest(BaseModel):
    platform_post_id: str
    connection: Connection


class DeleteRequest(BaseModel):
    platform_post_id: str
    connection: Connection


class FetchMetricsRequest(BaseModel):
    platform_post_id: str
    connection: Connection
    since: Optional[str] = None


class RefreshAuthRequest(BaseModel):
    connection: Connection


class BuildAssistPackRequest(BaseModel):
    rendition: Rendition
    destination: Destination
