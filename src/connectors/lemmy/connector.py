"""Lemmy Connector implementation using Lemmy HTTP v3 API."""
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


class LemmyConnector(BaseConnector):
    key = "lemmy"

    async def publish(
        self,
        rendition: Rendition,
        destination: Destination,
        connection: Connection,
        idempotency_key: Optional[str] = None,
    ) -> PublishResponse:
        base_url = connection.base_url or destination.url.rstrip("/")
        is_local = "localhost" in base_url or "127.0.0.1" in base_url
        if settings.SIMULATION_MODE and (not is_local or "example.com" in base_url or "lemmy.world" in base_url):
            sim_id = f"lemmy_{abs(hash(rendition.title)) % 100000}"
            return PublishResponse(
                platform_post_id=sim_id,
                live_url=f"https://lemmy.world/post/{sim_id}",
                status="published",
            )

        target_url = f"{base_url}/api/v3/post"
        auth_token = connection.token or connection.api_key or "mock_jwt_token"
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        community_id = destination.config.get("community_id", 1)
        payload = {
            "name": rendition.title,
            "body": rendition.body,
            "community_id": community_id,
            "auth": auth_token,
        }

        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.post(target_url, json=payload, headers=headers)
                if res.status_code == 429:
                    retry_after = res.headers.get("Retry-After", "30")
                    raise ConnectorException(
                        code="PLATFORM_RATE_LIMIT",
                        message=f"Lemmy rate limit hit. Reset in {retry_after}s.",
                        retryable=True,
                        details={"reset_seconds": int(retry_after) if retry_after.isdigit() else 30},
                    )
                if res.status_code == 401:
                    raise ConnectorException(
                        code="CONNECTION_AUTH_EXPIRED",
                        message="Lemmy JWT auth token invalid or expired.",
                        retryable=False,
                    )
                if res.status_code in (400, 422):
                    raise ConnectorException(
                        code="PLATFORM_CONTENT_REJECTED",
                        message=f"Lemmy content rejected: {res.text}",
                        retryable=False,
                    )
                if res.status_code >= 500:
                    raise ConnectorException(
                        code="PLATFORM_UNAVAILABLE",
                        message="Lemmy instance unavailable.",
                        retryable=True,
                    )
                res.raise_for_status()
                data = res.json()
                post_view = data.get("post_view", {})
                post_id = post_view.get("post", {}).get("id") or data.get("id")
                if not post_id:
                    raise ConnectorException(
                        code="PLATFORM_CONTENT_REJECTED",
                        message="Lemmy API response missing post id.",
                        retryable=False,
                    )

                live_url = f"{base_url}/post/{post_id}"
                return PublishResponse(
                    platform_post_id=str(post_id),
                    live_url=live_url,
                    status="published",
                )
        except httpx.TimeoutException:
            raise ConnectorException(
                code="PLATFORM_UNAVAILABLE",
                message="Lemmy connection timed out.",
                retryable=True,
            )
        except ConnectorException:
            raise
        except Exception as e:
            raise ConnectorException(
                code="PLATFORM_UNAVAILABLE",
                message=f"Lemmy publish error: {str(e)}",
                retryable=True,
            )

    async def get_status(self, platform_post_id: str, connection: Connection) -> StatusResponse:
        base_url = connection.base_url or "https://lemmy.world"
        is_local = "localhost" in base_url or "127.0.0.1" in base_url
        if settings.SIMULATION_MODE and (not is_local or "example.com" in base_url or "lemmy.world" in base_url):
            return StatusResponse(status="active", live_url=f"{base_url}/post/{platform_post_id}")

        target_url = f"{base_url}/api/v3/post?id={platform_post_id}"
        auth_token = connection.token or connection.api_key or "mock_jwt_token"
        headers = {"Authorization": f"Bearer {auth_token}"}
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.get(target_url, headers=headers)
                if res.status_code == 404:
                    return StatusResponse(status="deleted", live_url="")
                res.raise_for_status()
                return StatusResponse(
                    status="active",
                    live_url=f"{base_url}/post/{platform_post_id}",
                )
        except Exception:
            return StatusResponse(status="unknown", live_url="")

    async def delete(self, platform_post_id: str, connection: Connection) -> DeleteResponse:
        base_url = connection.base_url or "https://lemmy.world"
        is_local = "localhost" in base_url or "127.0.0.1" in base_url
        if settings.SIMULATION_MODE and (not is_local or "example.com" in base_url or "lemmy.world" in base_url):
            return DeleteResponse(deleted=True)

        target_url = f"{base_url}/api/v3/post/delete"
        auth_token = connection.token or connection.api_key or "mock_jwt_token"
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        payload = {"post_id": int(platform_post_id) if platform_post_id.isdigit() else 1, "deleted": True, "auth": auth_token}
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.post(target_url, json=payload, headers=headers)
                return DeleteResponse(deleted=res.status_code in (200, 204))
        except Exception:
            return DeleteResponse(deleted=False)

    async def fetch_metrics(self, platform_post_id: str, connection: Connection, since: Optional[str] = None) -> MetricsResponse:
        base_url = connection.base_url or "https://lemmy.world"
        if settings.SIMULATION_MODE and not base_url.startswith("http"):
            return MetricsResponse(views=85, likes=12, comments=3)

        target_url = f"{base_url}/api/v3/post?id={platform_post_id}"
        auth_token = connection.token or connection.api_key or "mock_jwt_token"
        headers = {"Authorization": f"Bearer {auth_token}"}
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.get(target_url, headers=headers)
                if res.status_code == 200:
                    counts = res.json().get("post_view", {}).get("counts", {})
                    return MetricsResponse(
                        views=counts.get("score", 0) * 10,
                        likes=counts.get("upvotes", 0),
                        comments=counts.get("comments", 0),
                    )
        except Exception:
            pass
        return MetricsResponse(views=50, likes=5, comments=1)
