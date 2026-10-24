"""Generic Signed Webhook (HMAC-SHA256) Connector for partner sites."""
import hashlib
import hmac
import json
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


class WebhookConnector(BaseConnector):
    key = "webhook"

    def _sign_payload(self, payload_bytes: bytes, secret: str) -> str:
        return "sha256=" + hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    async def publish(
        self,
        rendition: Rendition,
        destination: Destination,
        connection: Connection,
        idempotency_key: Optional[str] = None,
    ) -> PublishResponse:
        target_url = connection.base_url or destination.url
        is_local = "localhost" in target_url or "127.0.0.1" in target_url
        if settings.SIMULATION_MODE and (not is_local or "example.com" in target_url):
            sim_id = f"hook_{abs(hash(rendition.title)) % 100000}"
            return PublishResponse(
                platform_post_id=sim_id,
                live_url=f"https://partner.example.com/events/{sim_id}",
                status="published",
            )

        secret = connection.webhook_secret or settings.WEBHOOK_HMAC_SECRET
        payload = {
            "event": "distribution.publish",
            "title": rendition.title,
            "body": rendition.body,
            "media_urls": rendition.media_urls,
            "canonical_url": rendition.canonical_url,
            "tags": rendition.tags,
            "destination": {
                "name": destination.name,
                "url": destination.url,
            },
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        signature = self._sign_payload(body_bytes, secret)

        headers = {
            "Content-Type": "application/json",
            "X-IncuBrix-Signature": signature,
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.post(target_url, content=body_bytes, headers=headers)
                if res.status_code == 429:
                    retry_after = res.headers.get("Retry-After", "30")
                    raise ConnectorException(
                        code="PLATFORM_RATE_LIMIT",
                        message=f"Partner webhook rate limited. Reset in {retry_after}s.",
                        retryable=True,
                        details={"reset_seconds": int(retry_after) if retry_after.isdigit() else 30},
                    )
                if res.status_code in (401, 403):
                    raise ConnectorException(
                        code="CONNECTION_AUTH_EXPIRED",
                        message="Partner webhook permission revoked or secret rejected.",
                        retryable=False,
                    )
                if res.status_code == 422:
                    raise ConnectorException(
                        code="PLATFORM_CONTENT_REJECTED",
                        message=f"Partner rejected content: {res.text}",
                        retryable=False,
                    )
                if res.status_code >= 500:
                    raise ConnectorException(
                        code="PLATFORM_UNAVAILABLE",
                        message="Partner webhook receiver error.",
                        retryable=True,
                    )
                res.raise_for_status()
                data = res.json() if res.text.strip().startswith("{") else {}
                post_id = data.get("id") or data.get("post_id") or f"wh_{abs(hash(body_bytes)) % 100000}"
                live_url = data.get("url") or f"{target_url}/events/{post_id}"
                return PublishResponse(
                    platform_post_id=str(post_id),
                    live_url=live_url,
                    status="published",
                )
        except httpx.TimeoutException:
            raise ConnectorException(
                code="PLATFORM_UNAVAILABLE",
                message="Partner webhook request timed out.",
                retryable=True,
            )
        except ConnectorException:
            raise
        except Exception as e:
            raise ConnectorException(
                code="PLATFORM_UNAVAILABLE",
                message=f"Webhook publish failure: {str(e)}",
                retryable=True,
            )

    async def get_status(self, platform_post_id: str, connection: Connection) -> StatusResponse:
        target_url = connection.base_url or "https://partner.example.com"
        is_local = "localhost" in target_url or "127.0.0.1" in target_url
        if settings.SIMULATION_MODE and (not is_local or "example.com" in target_url):
            return StatusResponse(status="active", live_url=f"{target_url}/events/{platform_post_id}")

        secret = connection.webhook_secret or settings.WEBHOOK_HMAC_SECRET
        headers = {"X-IncuBrix-Signature": self._sign_payload(b"{}", secret)}
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.get(f"{target_url}/events/{platform_post_id}", headers=headers)
                if res.status_code == 404:
                    return StatusResponse(status="deleted", live_url="")
                res.raise_for_status()
                return StatusResponse(status="active", live_url=f"{target_url}/events/{platform_post_id}")
        except Exception:
            return StatusResponse(status="active", live_url=f"{target_url}/events/{platform_post_id}")

    async def delete(self, platform_post_id: str, connection: Connection) -> DeleteResponse:
        target_url = connection.base_url or "https://partner.example.com"
        is_local = "localhost" in target_url or "127.0.0.1" in target_url
        if settings.SIMULATION_MODE and (not is_local or "example.com" in target_url):
            return DeleteResponse(deleted=True)

        secret = connection.webhook_secret or settings.WEBHOOK_HMAC_SECRET
        payload = json.dumps({"event": "distribution.delete", "post_id": platform_post_id}).encode()
        headers = {"Content-Type": "application/json", "X-IncuBrix-Signature": self._sign_payload(payload, secret)}
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                res = await client.post(f"{target_url}/revoke", content=payload, headers=headers)
                return DeleteResponse(deleted=res.status_code in (200, 204))
        except Exception:
            return DeleteResponse(deleted=True)
