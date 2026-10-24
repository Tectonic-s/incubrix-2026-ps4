"""Assisted Connector for destinations where automation is not allowed."""
from typing import Optional

from src.connectors.base import BaseConnector
from src.models.connector import (
    AssistPackResponse,
    Connection,
    DeleteResponse,
    Destination,
    PublishResponse,
    Rendition,
    StatusResponse,
)


class AssistedConnector(BaseConnector):
    key = "assisted"

    async def build_assist_pack(self, rendition: Rendition, destination: Destination) -> AssistPackResponse:
        # Build checklist based on destination rules
        checklist = [
            f"Review community guidelines at {destination.rules_url or destination.url}",
            f"Ensure frequency cap ({destination.frequency_cap}) has not been breached",
        ]
        if not destination.self_promo_allowed:
            checklist.append("DO NOT include direct promotional claims or affiliate sales pitches")
        if destination.disclosure_required:
            checklist.append("Verify AI generation disclosure is clearly visible in the text")
        if destination.link_policy == "no_affiliate":
            checklist.append("Ensure no affiliate or UTM tracking query parameters are present")
        elif destination.link_policy == "banned":
            checklist.append("Ensure all external hyperlinks have been stripped from the submission")

        caption_parts = [rendition.title, "\n\n", rendition.body]
        if destination.disclosure_required and rendition.has_ai_disclosure:
            caption_parts.append("\n\n[AI Transparency: Content created with AI assistance]")
        if rendition.tags:
            caption_parts.append("\n\n" + " ".join(f"#{t.replace(' ', '')}" for t in rendition.tags))

        deep_link = destination.url
        if not deep_link.endswith("/submit") and not deep_link.endswith("/new"):
            if "reddit" in deep_link or "forum" in deep_link:
                deep_link = f"{deep_link.rstrip('/')}/submit"

        return AssistPackResponse(
            files=rendition.media_urls,
            caption="".join(caption_parts),
            deep_link=deep_link,
            checklist=checklist,
        )

    async def publish(
        self,
        rendition: Rendition,
        destination: Destination,
        connection: Connection,
        idempotency_key: Optional[str] = None,
    ) -> PublishResponse:
        pack = await self.build_assist_pack(rendition, destination)
        pack_id = f"assist_{abs(hash(rendition.title + destination.name)) % 100000}"
        return PublishResponse(
            platform_post_id=pack_id,
            live_url=pack.deep_link,
            status="ready_for_manual_post",
        )

    async def get_status(self, platform_post_id: str, connection: Connection) -> StatusResponse:
        return StatusResponse(status="ready_for_manual_post", live_url="")

    async def delete(self, platform_post_id: str, connection: Connection) -> DeleteResponse:
        # Assisted posts are stored locally in the pack registry
        return DeleteResponse(deleted=True)
