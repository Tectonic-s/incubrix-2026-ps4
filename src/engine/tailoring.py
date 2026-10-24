"""Content Tailoring Engine adapting title, text, tags, and canonical URLs per destination."""
import re
from typing import Dict, List, Optional
from src.models.connector import Destination, Rendition
from src.connectors.registry import registry


class TailoringEngine:
    @staticmethod
    def truncate_at_word(text: str, max_chars: int, suffix: str = "...") -> str:
        """Truncates text at the nearest preceding word boundary."""
        if len(text) <= max_chars:
            return text
        target_len = max_chars - len(suffix)
        if target_len <= 0:
            return text[:max_chars]
        truncated = text[:target_len]
        last_space = truncated.rfind(" ")
        if last_space > 0:
            return truncated[:last_space].rstrip(",;:. ") + suffix
        return truncated + suffix

    def frame_discussion_first(self, title: str, body: str) -> (str, str):
        """Frames content for discussion forums with open engagement hooks."""
        # Convert declarative title to discussion prompt if not already a question
        tailored_title = title.strip()
        if not tailored_title.endswith("?"):
            if not tailored_title.lower().startswith(("how", "what", "why", "does", "is", "should")):
                tailored_title = f"What are your thoughts on: {tailored_title}?"

        # Append engaging discussion question to body
        discussion_hook = (
            "\n\n---\n"
            "**Discussion Question:** Have you implemented a similar approach in your workflow? "
            "What challenges or trade-offs did you encounter?"
        )
        tailored_body = body + discussion_hook
        return tailored_title, tailored_body

    def format_tags(self, tags: List[str], connector_key: str) -> List[str]:
        """Formats tags according to platform style guides."""
        formatted = []
        for t in tags:
            clean = re.sub(r"[^\w\s-]", "", t).strip()
            if not clean:
                continue
            if connector_key in ("discourse", "lemmy", "devto"):
                # Clean lowercase dash-separated
                formatted.append(clean.lower().replace(" ", "-"))
            elif connector_key == "slack":
                # Slack hashtag format
                formatted.append(f"#{clean.replace(' ', '_')}")
            else:
                formatted.append(clean.lower())
        return formatted[:5]

    def tailor(self, rendition: Rendition, destination: Destination) -> Rendition:
        """Produces a tailored rendition fitting the destination limits and cultural norms."""
        connector = registry.get(destination.connector_key)
        spec = connector.get_surface_spec(destination.surface)

        title = rendition.title
        body = rendition.body
        canonical_url = rendition.canonical_url

        # 1. Discussion framing for forums
        if destination.surface in ("topic", "thread") or destination.connector_key in ("discourse", "lemmy"):
            title, body = self.frame_discussion_first(title, body)

        # 2. Canonical URL for articles
        if destination.connector_key in ("devto", "ghost", "hashnode"):
            if not canonical_url and destination.url:
                canonical_url = destination.config.get("canonical_source_url") or "https://incubrix.com/blog/original"

        # 3. Truncation at word boundary according to spec
        title_max = spec.get("title_max_chars", 255)
        body_max = spec.get("body_max_chars", 32000)

        title = self.truncate_at_word(title, title_max)
        body = self.truncate_at_word(body, body_max)

        # 4. Platform specific tags
        tags = self.format_tags(rendition.tags, destination.connector_key)

        return Rendition(
            title=title,
            body=body,
            media_urls=rendition.media_urls,
            tags=tags,
            canonical_url=canonical_url,
            is_promotional=rendition.is_promotional,
            has_ai_disclosure=rendition.has_ai_disclosure,
            extra_meta=rendition.extra_meta,
        )


tailoring_engine = TailoringEngine()
