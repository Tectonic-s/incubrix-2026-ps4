"""Slack Bridge Connector for community channels."""
from typing import Optional
import httpx

from src.config import settings
from src.connectors.base import BaseConnector, ConnectorException
from src.models.connector import (
    Connection,
    DeleteResponse,
    Destination,
    PublishResponse,
    Rendition,
    StatusResponse,
)


class SlackConnector(BaseConnector):
    key = "slack"

    async def publish(
        self,
        rendition: Rendition,
        destination: Destination,
        connection: Connection,
        idempotency_key: Optional[str] = None,
    ) -> PublishResponse:
        base_url = connection.base_url or "https://slack.com/api"
        if settings.SIMULATION_MODE and not base_url.startswith("http"):
            sim_id = f"171{abs(hash(rendition.title)) % 1000000}.001200"
            return PublishResponse(
                platform_post_id=sim_id,
                live_url=f"https://slack.com/archives/C12345/p{sim_id.replace('.', '')}",
                status="published",
            )

        token = connection.token or connection.api_key or "mock_xoxb_token"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        channel = destination.config.get("channel_id", "general")

        text = f"*{rendition.title}*\n\n{rendition.body}"
        payload = {"channel": channel, "text": text}

        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.post(f"{base_url.rstrip('/')}/chat.postMessage", json=payload, headers=headers)
                if res.status_code == 429:
                    raise ConnectorException(code="PLATFORM_RATE_LIMIT", message="Slack rate limit exceeded.", retryable=True)
                res.raise_for_status()
                data = res.json()
                if not data.get("ok"):
                    error_str = data.get("error", "slack_error")
                    if error_str in ("invalid_auth", "token_revoked"):
                        raise ConnectorException(code="CONNECTION_AUTH_EXPIRED", message=f"Slack auth error: {error_str}", retryable=False)
                    raise ConnectorException(code="PLATFORM_CONTENT_REJECTED", message=f"Slack error: {error_str}", retryable=False)
                
                ts = data.get("ts", "0")
                channel_out = data.get("channel", channel)
                return PublishResponse(
                    platform_post_id=ts,
                    live_url=f"https://slack.com/archives/{channel_out}/p{ts.replace('.', '')}",
                    status="published",
                )
        except ConnectorException:
            raise
        except Exception as e:
            raise ConnectorException(code="PLATFORM_UNAVAILABLE", message=f"Slack error: {str(e)}", retryable=True)

    async def get_status(self, platform_post_id: str, connection: Connection) -> StatusResponse:
        return StatusResponse(status="active", live_url="")

    async def delete(self, platform_post_id: str, connection: Connection) -> DeleteResponse:
        return DeleteResponse(deleted=True)
