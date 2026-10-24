"""MRSS (Media RSS) Feed Connector for CTV and video aggregators."""
from datetime import datetime, timezone
from typing import Optional
from xml.sax.saxutils import escape

from src.connectors.base import BaseConnector
from src.models.connector import (
    Connection,
    DeleteResponse,
    Destination,
    PublishResponse,
    Rendition,
    StatusResponse,
)


class MRSSConnector(BaseConnector):
    key = "mrss"

    async def publish(
        self,
        rendition: Rendition,
        destination: Destination,
        connection: Connection,
        idempotency_key: Optional[str] = None,
    ) -> PublishResponse:
        item_id = f"mrss_{abs(hash(rendition.title + destination.name)) % 100000}"
        media_url = rendition.media_urls[0] if rendition.media_urls else "https://video.example.com/asset.mp4"
        now_str = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

        # Format MRSS item XML
        mrss_xml = f"""<item>
    <title>{escape(rendition.title)}</title>
    <description>{escape(rendition.body[:500])}</description>
    <pubDate>{now_str}</pubDate>
    <guid isPermaLink="false">{item_id}</guid>
    <media:content url="{escape(media_url)}" medium="video" type="video/mp4" />
</item>"""
        live_url = f"{destination.url.rstrip('/')}/items/{item_id}.xml"
        return PublishResponse(
            platform_post_id=item_id,
            live_url=live_url,
            status="published",
        )

    async def get_status(self, platform_post_id: str, connection: Connection) -> StatusResponse:
        return StatusResponse(status="active", live_url=f"https://feeds.example.com/items/{platform_post_id}.xml")

    async def delete(self, platform_post_id: str, connection: Connection) -> DeleteResponse:
        return DeleteResponse(deleted=True)
