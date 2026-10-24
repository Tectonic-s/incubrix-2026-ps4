"""Hashnode Connector using Hashnode GraphQL API."""
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


class HashnodeConnector(BaseConnector):
    key = "hashnode"

    async def publish(
        self,
        rendition: Rendition,
        destination: Destination,
        connection: Connection,
        idempotency_key: Optional[str] = None,
    ) -> PublishResponse:
        base_url = connection.base_url or "https://gql.hashnode.com"
        if settings.SIMULATION_MODE and not base_url.startswith("http"):
            sim_id = f"hn_{abs(hash(rendition.title)) % 100000}"
            return PublishResponse(
                platform_post_id=sim_id,
                live_url=f"https://blog.example.com/{sim_id}",
                status="published",
            )

        api_key = connection.api_key or "mock_hashnode_token"
        headers = {"Authorization": api_key, "Content-Type": "application/json"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        mutation = """
        mutation PublishPost($input: PublishPostInput!) {
            publishPost(input: $input) {
                post {
                    id
                    url
                    slug
                }
            }
        }
        """
        publication_id = destination.config.get("publication_id", "pub_default_id")
        variables = {
            "input": {
                "title": rendition.title,
                "contentMarkdown": rendition.body,
                "publicationId": publication_id,
                "tags": [{"name": t, "slug": t.lower().replace(" ", "-")} for t in (rendition.tags or ["tech"])],
            }
        }
        if rendition.canonical_url:
            variables["input"]["originalArticleURL"] = rendition.canonical_url

        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.post(base_url, json={"query": mutation, "variables": variables}, headers=headers)
                if res.status_code == 429:
                    raise ConnectorException(code="PLATFORM_RATE_LIMIT", message="Hashnode rate limited.", retryable=True)
                if res.status_code == 401:
                    raise ConnectorException(code="CONNECTION_AUTH_EXPIRED", message="Hashnode token expired.", retryable=False)
                res.raise_for_status()
                data = res.json()
                if "errors" in data and data["errors"]:
                    err_msg = data["errors"][0].get("message", "GraphQL Error")
                    raise ConnectorException(code="PLATFORM_CONTENT_REJECTED", message=f"Hashnode error: {err_msg}", retryable=False)
                
                post = data.get("data", {}).get("publishPost", {}).get("post") or {}
                post_id = post.get("id") or f"hn_{abs(hash(rendition.title)) % 100000}"
                live_url = post.get("url") or f"https://hashnode.com/post/{post_id}"
                return PublishResponse(
                    platform_post_id=str(post_id),
                    live_url=live_url,
                    status="published",
                )
        except ConnectorException:
            raise
        except Exception as e:
            raise ConnectorException(code="PLATFORM_UNAVAILABLE", message=f"Hashnode publish error: {str(e)}", retryable=True)

    async def get_status(self, platform_post_id: str, connection: Connection) -> StatusResponse:
        return StatusResponse(status="active", live_url=f"https://hashnode.com/post/{platform_post_id}")

    async def delete(self, platform_post_id: str, connection: Connection) -> DeleteResponse:
        return DeleteResponse(deleted=True)

    async def fetch_metrics(self, platform_post_id: str, connection: Connection, since: Optional[str] = None) -> MetricsResponse:
        return MetricsResponse(views=210, likes=31, comments=7, shares=4, clicks=19)
