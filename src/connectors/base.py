"""Base connector interface and error handling conforming to Appendix A."""
import abc
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from src.models.connector import (
    AssistPackResponse,
    Connection,
    DeleteResponse,
    Destination,
    MetricsResponse,
    PublishResponse,
    RefreshAuthResponse,
    Rendition,
    StatusResponse,
    ValidateResponse,
)


class ConnectorException(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False, details: Any = None, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details
        self.status_code = status_code

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "retryable": self.retryable,
                "details": self.details,
            }
        }


class BaseConnector(abc.ABC):
    key: str = ""
    version: str = "1.0.0"

    def __init__(self):
        self.manifest = self.load_manifest()

    def load_manifest(self) -> Dict[str, Any]:
        manifest_path = Path(__file__).parent / self.key / "manifest.yaml"
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {}

    def get_surface_spec(self, surface_key: str = "topic") -> Dict[str, Any]:
        surfaces = self.manifest.get("surfaces", [])
        for surface in surfaces:
            if surface.get("key") == surface_key:
                return surface.get("spec", {})
        if surfaces:
            return surfaces[0].get("spec", {})
        return {"title_max_chars": 255, "body_max_chars": 32000, "links_allowed": True}

    def validate_spec(self, rendition: Rendition, surface_key: str = "topic") -> List[str]:
        violations = []
        spec = self.get_surface_spec(surface_key)
        
        title_max = spec.get("title_max_chars", 255)
        if len(rendition.title) > title_max:
            violations.append(f"Title length {len(rendition.title)} exceeds limit of {title_max} characters.")

        body_max = spec.get("body_max_chars", 32000)
        if len(rendition.body) > body_max:
            violations.append(f"Body length {len(rendition.body)} exceeds limit of {body_max} characters.")

        links_allowed = spec.get("links_allowed", True)
        if not links_allowed and ("http://" in rendition.body or "https://" in rendition.body):
            violations.append("Links are not permitted on this destination surface.")

        allowed_content_types = spec.get("content_types", ["text", "image", "video_link"])
        if rendition.media_urls:
            for url in rendition.media_urls:
                lower = url.lower()
                is_video = lower.endswith((".mp4", ".mov", ".webm"))
                is_image = lower.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp"))
                if is_video and "video_link" not in allowed_content_types and "video" not in allowed_content_types:
                    violations.append(f"Video media {url} not supported by surface.")
                elif is_image and "image" not in allowed_content_types:
                    violations.append(f"Image media {url} not supported by surface.")

        return violations

    def validate(self, rendition: Rendition, destination: Destination, connection: Connection) -> ValidateResponse:
        violations = self.validate_spec(rendition, destination.surface)
        return ValidateResponse(ok=len(violations) == 0, violations=violations)

    @abc.abstractmethod
    async def publish(
        self,
        rendition: Rendition,
        destination: Destination,
        connection: Connection,
        idempotency_key: Optional[str] = None,
    ) -> PublishResponse:
        pass

    @abc.abstractmethod
    async def get_status(self, platform_post_id: str, connection: Connection) -> StatusResponse:
        pass

    @abc.abstractmethod
    async def delete(self, platform_post_id: str, connection: Connection) -> DeleteResponse:
        pass

    async def fetch_metrics(self, platform_post_id: str, connection: Connection, since: Optional[str] = None) -> MetricsResponse:
        return MetricsResponse()

    async def refresh_auth(self, connection: Connection) -> RefreshAuthResponse:
        return RefreshAuthResponse(expires_at="2099-12-31T23:59:59Z")

    async def build_assist_pack(self, rendition: Rendition, destination: Destination) -> AssistPackResponse:
        raise ConnectorException(
            code="DEST_SPEC_VIOLATION",
            message="build_assist_pack is only supported on assisted tier connectors",
            retryable=False,
        )
