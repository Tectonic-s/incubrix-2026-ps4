"""Posting-Rules Engine checking destination policies before every post."""
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.connectors.base import ConnectorException
from src.database import get_db
from src.models.connector import Destination, Rendition


class RulesEngine:
    AFFILIATE_PARAMS = ["ref", "aff", "affiliate", "tag", "utm_campaign", "partner"]
    PROMO_KEYWORDS = ["buy now", "discount", "limited offer", "coupon", "special deal", "sign up today", "50% off"]

    @staticmethod
    def parse_frequency_cap(cap_str: str) -> Tuple[int, timedelta]:
        """Parses frequency cap expressions like '1/7d', '2/24h', '5/30d'."""
        match = re.match(r"^(\d+)/(\d+)([dh])$", cap_str.strip().lower())
        if not match:
            # Default 1 post per 7 days
            return 1, timedelta(days=7)
        count = int(match.group(1))
        unit_val = int(match.group(2))
        unit = match.group(3)
        delta = timedelta(days=unit_val) if unit == "d" else timedelta(hours=unit_val)
        return count, delta

    def check_frequency_cap(self, destination: Destination) -> Tuple[bool, Optional[str], Optional[datetime]]:
        """Checks if destination frequency cap has been breached."""
        max_posts, window = self.parse_frequency_cap(destination.frequency_cap)
        since_time = datetime.now(timezone.utc) - window
        since_iso = since_time.isoformat()

        with get_db() as conn:
            cur = conn.execute(
                """
                SELECT COUNT(*), MAX(published_at) FROM posts
                WHERE destination_id = ? AND published_at > ? AND status = 'published'
                """,
                (destination.id or destination.name, since_iso),
            )
            row = cur.fetchone()
            recent_count = row[0] if row else 0
            last_published = row[1] if row and row[1] else None

        if recent_count >= max_posts:
            # Calculate when the next post is allowed
            last_dt = datetime.fromisoformat(last_published) if last_published else datetime.now(timezone.utc)
            reschedule_at = last_dt + window
            msg = f"Frequency cap reached ({destination.frequency_cap}). Next eligible post at {reschedule_at.isoformat()}."
            return False, msg, reschedule_at
        return True, None, None

    def check_rules(self, rendition: Rendition, destination: Destination) -> Dict[str, Any]:
        """
        Validates all posting rules before publication.
        Raises ConnectorException with standard code if a rule fails.
        """
        violations: List[str] = []

        # 1. Frequency Cap Check
        ok_freq, freq_msg, reschedule_time = self.check_frequency_cap(destination)
        if not ok_freq:
            raise ConnectorException(
                code="DEST_RULE_FREQUENCY_CAP",
                message=freq_msg or "Frequency cap reached.",
                retryable=True,
                details={"reschedule_at": reschedule_time.isoformat() if reschedule_time else None},
            )

        # 2. Self-Promotion Policy Check
        is_promo = rendition.is_promotional
        if not is_promo:
            # Keyword heuristic check
            lower_body = (rendition.title + " " + rendition.body).lower()
            if any(kw in lower_body for kw in self.PROMO_KEYWORDS):
                is_promo = True

        if not destination.self_promo_allowed and is_promo:
            violations.append("Destination strictly bans self-promotion and promotional content.")

        # 3. Link Policy Check
        has_links = "http://" in rendition.body or "https://" in rendition.body
        if destination.link_policy == "banned" and has_links:
            violations.append("Hyperlinks are banned on this destination surface.")
        elif destination.link_policy == "no_affiliate" and has_links:
            # Check for affiliate tracking patterns
            for param in self.AFFILIATE_PARAMS:
                if f"{param}=" in rendition.body.lower():
                    violations.append(f"Affiliate tracking parameter '{param}' is prohibited by destination policy.")
                    break

        # 4. AI-Content Disclosure Check
        if destination.disclosure_required and not rendition.has_ai_disclosure:
            lower_body = rendition.body.lower()
            has_ai_kw = bool(re.search(r"\bai\b", lower_body))
            has_notice = has_ai_kw and any(w in lower_body for w in ("generated", "disclosure", "transparency", "assisted"))
            if not has_notice:
                violations.append("Destination requires explicit AI-content disclosure notice.")

        if violations:
            raise ConnectorException(
                code="DEST_SPEC_VIOLATION",
                message=f"Posting rule violations: {'; '.join(violations)}",
                retryable=False,
                details={"violations": violations},
            )

        return {"valid": True, "violations": []}


rules_engine = RulesEngine()
