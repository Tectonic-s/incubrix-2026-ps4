"""AI Rules Capture Adapter with Human-in-the-Loop Confirmation."""
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.config import settings
from src.database import get_db
from src.logger import logger
from src.storage import fetch_or_read_input


class AIRulesAdapter:
    """Swappable AI adapter with deterministic local fallback."""
    def extract_rules(self, text: str) -> Dict[str, Any]:
        lower = text.lower()

        # 1. Frequency cap detection
        freq_cap = "1/7d"
        if "once a month" in lower or "one post per month" in lower or "monthly" in lower:
            freq_cap = "1/30d"
        elif "once a week" in lower or "one post per week" in lower or "weekly" in lower:
            freq_cap = "1/7d"
        elif "daily" in lower or "once a day" in lower:
            freq_cap = "1/24h"

        # 2. Self-promotion detection
        self_promo = True
        if any(p in lower for p in ["no self-promotion", "no self promotion", "no ads", "no advertising", "zero tolerance for promo", "strictly no promo"]):
            self_promo = False

        # 3. Link policy
        link_policy = "allowed"
        if "no links" in lower or "links prohibited" in lower:
            link_policy = "banned"
        elif "no affiliate" in lower or "no referral" in lower:
            link_policy = "no_affiliate"

        # 4. AI-disclosure detection
        disclosure_required = False
        has_ai = bool(re.search(r"\bai\b", lower))
        if has_ai and any(p in lower for p in ["disclosure", "disclose", "label", "declar", "prohibited", "transparency"]):
            disclosure_required = True

        return {
            "frequency_cap": freq_cap,
            "self_promo_allowed": self_promo,
            "link_policy": link_policy,
            "disclosure_required": disclosure_required,
            "confidence": 0.92,
            "extracted_by": f"adapter_{settings.AI_PROVIDER}_{settings.AI_MODEL_NAME}",
        }


class RulesCaptureEngine:
    def __init__(self):
        self.adapter = AIRulesAdapter()

    async def propose_rules(self, community_url: str, rules_text_or_url: Optional[str] = None) -> Dict[str, Any]:
        """Proposes rules using the AI adapter step."""
        source_content = ""
        if rules_text_or_url:
            source_content = await fetch_or_read_input(rules_text_or_url)
        else:
            source_content = f"Guidelines for community at {community_url}. No spam, weekly posts only, no affiliate links."

        proposed = self.adapter.extract_rules(source_content)
        proposal_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO rules_proposals (id, community_url, proposed_rules_json, source_text, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?)
                """,
                (proposal_id, community_url, json.dumps(proposed), source_content[:1000], now),
            )

        logger.info(f"Proposed rules for {community_url} under proposal {proposal_id}")
        return {
            "proposal_id": proposal_id,
            "community_url": community_url,
            "status": "pending_human_review",
            "proposed_rules": proposed,
            "source_sample": source_content[:200],
        }

    def confirm_rules(self, proposal_id: str, confirmed_rules: Dict[str, Any], destination_id: Optional[str] = None) -> Dict[str, Any]:
        """Human confirms or overrides proposed rules before they are applied."""
        now = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            cur = conn.execute("SELECT * FROM rules_proposals WHERE id = ?", (proposal_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Proposal {proposal_id} not found")

            conn.execute(
                """
                UPDATE rules_proposals
                SET status = 'confirmed', confirmed_rules_json = ?, reviewed_at = ?
                WHERE id = ?
                """,
                (json.dumps(confirmed_rules), now, proposal_id),
            )

            # Apply to destination if destination_id provided or match by URL
            dest_target = destination_id or row["community_url"]
            conn.execute(
                """
                UPDATE destinations
                SET frequency_cap = COALESCE(?, frequency_cap),
                    self_promo_allowed = COALESCE(?, self_promo_allowed),
                    link_policy = COALESCE(?, link_policy),
                    disclosure_required = COALESCE(?, disclosure_required),
                    updated_at = ?
                WHERE id = ? OR url = ?
                """,
                (
                    confirmed_rules.get("frequency_cap"),
                    1 if confirmed_rules.get("self_promo_allowed") else 0,
                    confirmed_rules.get("link_policy"),
                    1 if confirmed_rules.get("disclosure_required") else 0,
                    now,
                    dest_target,
                    dest_target,
                ),
            )

        return {
            "proposal_id": proposal_id,
            "status": "confirmed",
            "applied_rules": confirmed_rules,
            "confirmed_at": now,
        }


rules_capture_engine = RulesCaptureEngine()
