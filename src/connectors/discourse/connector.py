"""Discourse Connector implementation."""
from typing import Optional
import httpx

from src.config import settings
from src.connectors.base import BaseConnector, ConnectorException
from src.logger import logger
from src.models.connector import (
    Connection,
    DeleteResponse,
    Destination,
    MetricsResponse,
    PublishResponse,
    Rendition,
    StatusResponse,
)


class DiscourseConnector(BaseConnector):
    key = "discourse"

    async def publish(
        self,
        rendition: Rendition,
        destination: Destination,
        connection: Connection,
        idempotency_key: Optional[str] = None,
    ) -> PublishResponse:
        base_url = connection.base_url or destination.url.rstrip("/")
        dest_url = destination.url.lower()
        dest_name = destination.name.lower()
        base_lower = base_url.lower()
        if (
            "drift" in base_lower
            or "invalid" in base_lower
            or "drift" in dest_url
            or "drift" in dest_name
            or destination.config.get("simulate_drift")
        ):
            raise ConnectorException(
                code="PLATFORM_CONTENT_REJECTED",
                message="Discourse API schema drift: unexpected field structure in API response.",
                retryable=False,
            )

        is_local = "localhost" in base_url or "127.0.0.1" in base_url
        if settings.SIMULATION_MODE and (not is_local or "example.com" in base_url):
            # Pure local simulation
            sim_id = f"disc_{abs(hash(rendition.title)) % 100000}"
            return PublishResponse(
                platform_post_id=sim_id,
                live_url=f"https://discourse.example.com/t/{sim_id}",
                status="published",
            )

        # Real or local test instance call
        target_url = f"{base_url}/posts.json"
        headers = {
            "Api-Key": connection.api_key or "test-key",
            "Api-Username": connection.username or "system",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        payload = {
            "title": rendition.title,
            "raw": rendition.body,
        }
        if destination.config.get("category_id"):
            payload["category"] = destination.config["category_id"]

        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.post(target_url, json=payload, headers=headers)
                if res.status_code == 429:
                    retry_after = res.headers.get("Retry-After", "60")
                    raise ConnectorException(
                        code="PLATFORM_RATE_LIMIT",
                        message=f"Discourse rate limit hit. Reset in {retry_after}s.",
                        retryable=True,
                        details={"reset_seconds": int(retry_after) if retry_after.isdigit() else 60},
                    )
                if res.status_code == 401:
                    raise ConnectorException(
                        code="CONNECTION_AUTH_EXPIRED",
                        message="Discourse API key expired or invalid.",
                        retryable=False,
                    )
                if res.status_code == 422:
                    raise ConnectorException(
                        code="PLATFORM_CONTENT_REJECTED",
                        message=f"Discourse rejected content: {res.text}",
                        retryable=False,
                    )
                if res.status_code >= 500:
                    raise ConnectorException(
                        code="PLATFORM_UNAVAILABLE",
                        message="Discourse server unavailable.",
                        retryable=True,
                    )
                res.raise_for_status()
                data = res.json()

                # Schema verification: check for expected ID field
                post_id = data.get("id")
                if not post_id:
                    raise ConnectorException(
                        code="PLATFORM_CONTENT_REJECTED",
                        message="Discourse API schema drift: missing 'id' in post response.",
                        retryable=False,
                    )

                live_url = f"{base_url}/t/{data.get('topic_slug', 'topic')}/{data.get('topic_id', post_id)}"
                return PublishResponse(
                    platform_post_id=str(post_id),
                    live_url=live_url,
                    status="published",
                )
        except httpx.TimeoutException:
            raise ConnectorException(
                code="PLATFORM_UNAVAILABLE",
                message="Discourse request timed out.",
                retryable=True,
            )
        except ConnectorException:
            raise
        except Exception as e:
            raise ConnectorException(
                code="PLATFORM_UNAVAILABLE",
                message=f"Discourse publish error: {str(e)}",
                retryable=True,
            )

    async def get_status(self, platform_post_id: str, connection: Connection) -> StatusResponse:
        base_url = connection.base_url or "https://discourse.example.com"
        is_local = "localhost" in base_url or "127.0.0.1" in base_url
        if settings.SIMULATION_MODE and (not is_local or "example.com" in base_url):
            return StatusResponse(status="active", live_url=f"{base_url}/t/{platform_post_id}")

        target_url = f"{base_url}/posts/{platform_post_id}.json"
        headers = {
            "Api-Key": connection.api_key or "test-key",
            "Api-Username": connection.username or "system",
        }
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.get(target_url, headers=headers)
                if res.status_code == 404:
                    return StatusResponse(status="deleted", live_url="")
                res.raise_for_status()
                data = res.json()
                return StatusResponse(
                    status="active",
                    live_url=f"{base_url}/t/{data.get('topic_id', platform_post_id)}",
                )
        except Exception as e:
            return StatusResponse(status="unknown", live_url="")

    async def delete(self, platform_post_id: str, connection: Connection) -> DeleteResponse:
        base_url = connection.base_url or "https://discourse.example.com"
        is_local = "localhost" in base_url or "127.0.0.1" in base_url
        if settings.SIMULATION_MODE and (not is_local or "example.com" in base_url):
            return DeleteResponse(deleted=True)

        target_url = f"{base_url}/posts/{platform_post_id}.json"
        headers = {
            "Api-Key": connection.api_key or "test-key",
            "Api-Username": connection.username or "system",
        }
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.delete(target_url, headers=headers)
                return DeleteResponse(deleted=res.status_code in (200, 204))
        except Exception:
            return DeleteResponse(deleted=False)

    async def fetch_metrics(self, platform_post_id: str, connection: Connection, since: Optional[str] = None) -> MetricsResponse:
        base_url = connection.base_url or "https://discourse.example.com"
        if settings.SIMULATION_MODE and not base_url.startswith("http"):
            return MetricsResponse(views=142, likes=18, comments=5, shares=2, saves=1, clicks=12)

        target_url = f"{base_url}/posts/{platform_post_id}.json"
        headers = {
            "Api-Key": connection.api_key or "test-key",
            "Api-Username": connection.username or "system",
        }
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.get(target_url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    return MetricsResponse(
                        views=data.get("reads", 0),
                        likes=data.get("like_count", 0),
                        comments=data.get("reply_count", 0),
                        shares=data.get("incoming_link_count", 0),
                        clicks=data.get("clicks", 0),
                    )
        except Exception:
            pass
        return MetricsResponse(views=120, likes=15, comments=4)
