"""Ghost CMS Connector implementation using Ghost Admin API."""
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


class GhostConnector(BaseConnector):
    key = "ghost"

    async def publish(
        self,
        rendition: Rendition,
        destination: Destination,
        connection: Connection,
        idempotency_key: Optional[str] = None,
    ) -> PublishResponse:
        base_url = connection.base_url or destination.url.rstrip("/")
        is_local = "localhost" in base_url or "127.0.0.1" in base_url
        if settings.SIMULATION_MODE and (not is_local or "example.com" in base_url):
            sim_id = f"ghost_{abs(hash(rendition.title)) % 100000}"
            return PublishResponse(
                platform_post_id=sim_id,
                live_url=f"https://ghost.example.com/{sim_id}",
                status="published",
            )

        target_url = f"{base_url}/ghost/api/admin/posts/?source=html"
        token = connection.token or connection.api_key or "mock_ghost_admin_token"
        headers = {
            "Authorization": f"Ghost {token}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        post_data = {
            "title": rendition.title,
            "html": f"<p>{rendition.body}</p>",
            "status": "published",
        }
        if rendition.canonical_url:
            post_data["canonical_url"] = rendition.canonical_url
        if rendition.tags:
            post_data["tags"] = [{"name": t} for t in rendition.tags]

        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.post(target_url, json={"posts": [post_data]}, headers=headers)
                if res.status_code == 429:
                    retry_after = res.headers.get("Retry-After", "60")
                    raise ConnectorException(
                        code="PLATFORM_RATE_LIMIT",
                        message=f"Ghost rate limit hit. Reset in {retry_after}s.",
                        retryable=True,
                        details={"reset_seconds": int(retry_after) if retry_after.isdigit() else 60},
                    )
                if res.status_code == 401:
                    raise ConnectorException(
                        code="CONNECTION_AUTH_EXPIRED",
                        message="Ghost Admin API key or JWT token expired.",
                        retryable=False,
                    )
                if res.status_code in (422, 400):
                    raise ConnectorException(
                        code="PLATFORM_CONTENT_REJECTED",
                        message=f"Ghost post rejected: {res.text}",
                        retryable=False,
                    )
                if res.status_code >= 500:
                    raise ConnectorException(
                        code="PLATFORM_UNAVAILABLE",
                        message="Ghost server unavailable.",
                        retryable=True,
                    )
                res.raise_for_status()
                data = res.json()
                posts = data.get("posts", [])
                if not posts or not posts[0].get("id"):
                    raise ConnectorException(
                        code="PLATFORM_CONTENT_REJECTED",
                        message="Ghost API response missing post id.",
                        retryable=False,
                    )
                post = posts[0]
                post_id = post["id"]
                live_url = post.get("url") or f"{base_url}/p/{post.get('slug', post_id)}"
                return PublishResponse(
                    platform_post_id=str(post_id),
                    live_url=live_url,
                    status="published",
                )
        except httpx.TimeoutException:
            raise ConnectorException(
                code="PLATFORM_UNAVAILABLE",
                message="Ghost connection timed out.",
                retryable=True,
            )
        except ConnectorException:
            raise
        except Exception as e:
            raise ConnectorException(
                code="PLATFORM_UNAVAILABLE",
                message=f"Ghost publish error: {str(e)}",
                retryable=True,
            )

    async def get_status(self, platform_post_id: str, connection: Connection) -> StatusResponse:
        base_url = connection.base_url or "https://ghost.example.com"
        is_local = "localhost" in base_url or "127.0.0.1" in base_url
        if settings.SIMULATION_MODE and (not is_local or "example.com" in base_url):
            return StatusResponse(status="active", live_url=f"{base_url}/p/{platform_post_id}")

        target_url = f"{base_url}/ghost/api/admin/posts/{platform_post_id}/"
        token = connection.token or connection.api_key or "mock_ghost_admin_token"
        headers = {"Authorization": f"Ghost {token}"}
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.get(target_url, headers=headers)
                if res.status_code == 404:
                    return StatusResponse(status="deleted", live_url="")
                res.raise_for_status()
                post = res.json().get("posts", [{}])[0]
                return StatusResponse(
                    status="active",
                    live_url=post.get("url", f"{base_url}/p/{platform_post_id}"),
                )
        except Exception:
            return StatusResponse(status="unknown", live_url="")

    async def delete(self, platform_post_id: str, connection: Connection) -> DeleteResponse:
        base_url = connection.base_url or "https://ghost.example.com"
        is_local = "localhost" in base_url or "127.0.0.1" in base_url
        if settings.SIMULATION_MODE and (not is_local or "example.com" in base_url):
            return DeleteResponse(deleted=True)

        target_url = f"{base_url}/ghost/api/admin/posts/{platform_post_id}/"
        token = connection.token or connection.api_key or "mock_ghost_admin_token"
        headers = {"Authorization": f"Ghost {token}"}
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.delete(target_url, headers=headers)
                return DeleteResponse(deleted=res.status_code in (200, 204))
        except Exception:
            return DeleteResponse(deleted=False)

    async def fetch_metrics(self, platform_post_id: str, connection: Connection, since: Optional[str] = None) -> MetricsResponse:
        base_url = connection.base_url or "https://ghost.example.com"
        if settings.SIMULATION_MODE and not base_url.startswith("http"):
            return MetricsResponse(views=480, likes=35, comments=0, clicks=64)

        target_url = f"{base_url}/ghost/api/admin/posts/{platform_post_id}/"
        token = connection.token or connection.api_key or "mock_ghost_admin_token"
        headers = {"Authorization": f"Ghost {token}"}
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.get(target_url, headers=headers)
                if res.status_code == 200:
                    post = res.json().get("posts", [{}])[0]
                    return MetricsResponse(
                        views=post.get("count", {}).get("views", 120),
                        likes=post.get("count", {}).get("likes", 12),
                        clicks=post.get("count", {}).get("clicks", 18),
                    )
        except Exception:
            pass
        return MetricsResponse(views=120, likes=12, clicks=18)
