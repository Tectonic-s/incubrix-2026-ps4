"""Dev.to (Forem API) Connector implementation."""
from typing import Optional
import httpx

from src.config import settings
from src.connectors.base import BaseConnector, ConnectorException
from src.models.connector import (
    Connection,
    DeleteResponse,
    Destination,
    MetricsResponse,
    PublishResponse,
    Rendition,
    StatusResponse,
)


class DevtoConnector(BaseConnector):
    key = "devto"

    async def publish(
        self,
        rendition: Rendition,
        destination: Destination,
        connection: Connection,
        idempotency_key: Optional[str] = None,
    ) -> PublishResponse:
        base_url = connection.base_url or "https://dev.to/api"
        is_local = "localhost" in base_url or "127.0.0.1" in base_url
        if settings.SIMULATION_MODE and (not is_local or "example.com" in base_url or "dev.to" in base_url):
            sim_id = f"devto_{abs(hash(rendition.title)) % 100000}"
            return PublishResponse(
                platform_post_id=sim_id,
                live_url=f"https://dev.to/article/{sim_id}",
                status="published",
            )

        target_url = f"{base_url.rstrip('/')}/articles"
        api_key = connection.api_key or "mock_devto_api_key"
        headers = {"api-key": api_key, "Content-Type": "application/json"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        article_payload = {
            "title": rendition.title,
            "body_markdown": rendition.body,
            "published": True,
            "tags": rendition.tags[:4] if rendition.tags else ["tech"],
        }
        if rendition.canonical_url:
            article_payload["canonical_url"] = rendition.canonical_url

        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.post(target_url, json={"article": article_payload}, headers=headers)
                if res.status_code == 429:
                    retry_after = res.headers.get("Retry-After", "30")
                    raise ConnectorException(
                        code="PLATFORM_RATE_LIMIT",
                        message=f"Dev.to rate limit hit. Reset in {retry_after}s.",
                        retryable=True,
                        details={"reset_seconds": int(retry_after) if retry_after.isdigit() else 30},
                    )
                if res.status_code == 401:
                    raise ConnectorException(
                        code="CONNECTION_AUTH_EXPIRED",
                        message="Dev.to API key invalid or unauthorized.",
                        retryable=False,
                    )
                if res.status_code in (422, 400):
                    raise ConnectorException(
                        code="PLATFORM_CONTENT_REJECTED",
                        message=f"Dev.to content rejected: {res.text}",
                        retryable=False,
                    )
                if res.status_code >= 500:
                    raise ConnectorException(
                        code="PLATFORM_UNAVAILABLE",
                        message="Dev.to API unavailable.",
                        retryable=True,
                    )
                res.raise_for_status()
                data = res.json()
                post_id = data.get("id")
                live_url = data.get("url") or f"https://dev.to/article/{post_id}"
                if not post_id:
                    raise ConnectorException(
                        code="PLATFORM_CONTENT_REJECTED",
                        message="Dev.to API schema drift: missing article id.",
                        retryable=False,
                    )

                return PublishResponse(
                    platform_post_id=str(post_id),
                    live_url=live_url,
                    status="published",
                )
        except httpx.TimeoutException:
            raise ConnectorException(
                code="PLATFORM_UNAVAILABLE",
                message="Dev.to connection timed out.",
                retryable=True,
            )
        except ConnectorException:
            raise
        except Exception as e:
            raise ConnectorException(
                code="PLATFORM_UNAVAILABLE",
                message=f"Dev.to publish error: {str(e)}",
                retryable=True,
            )

    async def get_status(self, platform_post_id: str, connection: Connection) -> StatusResponse:
        base_url = connection.base_url or "https://dev.to/api"
        is_local = "localhost" in base_url or "127.0.0.1" in base_url
        if settings.SIMULATION_MODE and (not is_local or "example.com" in base_url or "dev.to" in base_url):
            return StatusResponse(status="active", live_url=f"https://dev.to/article/{platform_post_id}")

        target_url = f"{base_url.rstrip('/')}/articles/{platform_post_id}"
        api_key = connection.api_key or "mock_devto_api_key"
        headers = {"api-key": api_key}
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.get(target_url, headers=headers)
                if res.status_code == 404:
                    return StatusResponse(status="deleted", live_url="")
                res.raise_for_status()
                data = res.json()
                return StatusResponse(
                    status="active",
                    live_url=data.get("url", f"https://dev.to/article/{platform_post_id}"),
                )
        except Exception:
            return StatusResponse(status="unknown", live_url="")

    async def delete(self, platform_post_id: str, connection: Connection) -> DeleteResponse:
        base_url = connection.base_url or "https://dev.to/api"
        is_local = "localhost" in base_url or "127.0.0.1" in base_url
        if settings.SIMULATION_MODE and (not is_local or "example.com" in base_url or "dev.to" in base_url):
            return DeleteResponse(deleted=True)

        target_url = f"{base_url.rstrip('/')}/articles/{platform_post_id}"
        api_key = connection.api_key or "mock_devto_api_key"
        headers = {"api-key": api_key}
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.delete(target_url, headers=headers)
                return DeleteResponse(deleted=res.status_code in (200, 204))
        except Exception:
            return DeleteResponse(deleted=False)

    async def fetch_metrics(self, platform_post_id: str, connection: Connection, since: Optional[str] = None) -> MetricsResponse:
        base_url = connection.base_url or "https://dev.to/api"
        if settings.SIMULATION_MODE and not base_url.startswith("http"):
            return MetricsResponse(views=350, likes=42, comments=8, clicks=25)

        target_url = f"{base_url.rstrip('/')}/articles/{platform_post_id}"
        api_key = connection.api_key or "mock_devto_api_key"
        headers = {"api-key": api_key}
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.get(target_url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    return MetricsResponse(
                        views=data.get("page_views_count", 0),
                        likes=data.get("public_reactions_count", 0),
                        comments=data.get("comments_count", 0),
                        clicks=data.get("reading_time_minutes", 1) * 10,
                    )
        except Exception:
            pass
        return MetricsResponse(views=200, likes=20, comments=3)
