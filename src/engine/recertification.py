"""Recertification Scheduler detecting schema drift and auto-demoting failing destinations."""
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from src.config import settings
from src.database import get_db
from src.engine.certification import certification_harness
from src.logger import logger
from src.models.connector import Connection, Destination


class RecertificationScheduler:
    async def run_recertification(self, force_all: bool = False) -> Dict[str, Any]:
        """
        Scans all certified destinations. Re-certifies any that haven't been tested within 30 days.
        Demotes failing destinations and generates alert tickets.
        """
        now = datetime.now(timezone.utc)
        threshold_date = now - timedelta(days=settings.RECERTIFICATION_INTERVAL_DAYS)

        destinations_to_check: List[Destination] = []
        with get_db() as conn:
            cur = conn.execute("SELECT * FROM destinations WHERE level IN ('L1', 'L2', 'L3', 'L4')")
            for r in cur.fetchall():
                last_cert = r["last_certified_at"]
                needs_check = force_all or not last_cert
                if not needs_check and last_cert:
                    try:
                        cert_dt = datetime.fromisoformat(last_cert)
                        if cert_dt < threshold_date:
                            needs_check = True
                    except Exception:
                        needs_check = True

                if needs_check:
                    tags = json.loads(r["audience_tags"]) if r["audience_tags"] else []
                    destinations_to_check.append(
                        Destination(
                            id=r["id"],
                            name=r["name"],
                            url=r["url"],
                            platform_key=r["platform_key"],
                            surface=r["surface"],
                            category=r["category"],
                            audience_tags=tags,
                            language=r["language"],
                            geo=r["geo"],
                            est_audience=r["est_audience"],
                            rules_url=r["rules_url"],
                            frequency_cap=r["frequency_cap"],
                            self_promo_allowed=bool(r["self_promo_allowed"]),
                            link_policy=r["link_policy"],
                            disclosure_required=bool(r["disclosure_required"]),
                            automation_allowed=bool(r["automation_allowed"]),
                            connector_key=r["connector_key"],
                            relevance_score=r["relevance_score"],
                            relevance_reason=r["relevance_reason"],
                            level=r["level"],
                            last_certified_at=r["last_certified_at"],
                            config=json.loads(r["config_json"]) if r["config_json"] else {},
                        )
                    )

        checked_count = len(destinations_to_check)
        passed_count = 0
        demoted_count = 0
        alerts: List[Dict[str, Any]] = []

        for dest in destinations_to_check:
            conn_config = Connection(
                base_url=dest.config.get("base_url") or dest.url,
                api_key=dest.config.get("api_key", "recert-key"),
            )
            result = await certification_harness.certify_destination(dest, conn_config)

            if result["status"] == "passed":
                passed_count += 1
            else:
                demoted_count += 1
                alert_id = str(uuid.uuid4())
                reason = result.get("error", "Certification verification failure / schema drift")
                alert_record = {
                    "alert_id": alert_id,
                    "destination_id": dest.id,
                    "destination_name": dest.name,
                    "reason": reason,
                    "previous_level": dest.level,
                    "new_level": "L0",
                    "timestamp": now.isoformat(),
                }
                alerts.append(alert_record)

                # Demote destination in DB & record alert
                with get_db() as db:
                    db.execute(
                        """
                        UPDATE destinations
                        SET level = 'L0', updated_at = ?
                        WHERE id = ?
                        """,
                        (now.isoformat(), dest.id),
                    )
                    db.execute(
                        """
                        INSERT INTO recertification_alerts (id, destination_id, reason, details_json, created_at, status)
                        VALUES (?, ?, ?, ?, ?, 'open')
                        """,
                        (alert_id, dest.id, reason, json.dumps(result), now.isoformat()),
                    )
                logger.warning(f"DEMOTION ALERT: Destination {dest.name} demoted to L0 due to: {reason}")

        return {
            "destinations_checked": checked_count,
            "passed_count": passed_count,
            "demoted_count": demoted_count,
            "alerts": alerts,
            "executed_at": now.isoformat(),
        }


recertification_scheduler = RecertificationScheduler()
