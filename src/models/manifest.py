"""Data models for background jobs and output manifests."""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int = Field(default=0, ge=0, le=100)
    result_links: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class OutputManifest(BaseModel):
    models_providers: Dict[str, Any] = Field(default_factory=dict)
    version: str = "1.0.0"
    settings: Dict[str, Any] = Field(default_factory=dict)
    seed: int = 42
    timings_ms: Dict[str, float] = Field(default_factory=dict)
    cost_estimate_usd: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    licence_rights: str = "Commercial use permitted under IncuBrix Integration Standards"
