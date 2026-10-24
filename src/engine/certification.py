"""Certification Harness for validating and certifying destinations end-to-end."""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from src.config import settings
from src.connectors.base import BaseConnector, ConnectorException
from src.connectors.registry import registry
from src.database import get_db
from src.logger import logger
from src.models.connector import Connection, Destination, Rendition


class CertificationHarness:
    def __init__(self, pack_dir: str = "./certification_pack"):
        self.pack_dir = Path(pack_dir)
        self.pack_dir.mkdir(parents=True, exist_ok=True)

    async def certify_destination(self, destination: Destination, connection: Connection) -> Dict[str, Any]:
        """
        Executes a 4-step certification pipeline:
        1. Publish test post
        2. Confirm live URL & status
        3. Read metrics (optional, checks for L4)
        4. Clean up / delete within 10 minutes
        """
        cert_id = str(uuid.uuid4())
        connector = registry.get(destination.connector_key)
        start_time = datetime.now(timezone.utc)

        evidence: Dict[str, Any] = {
            "certification_id": cert_id,
            "destination_name": destination.name,
            "destination_url": destination.url,
            "connector_key": destination.connector_key,
            "started_at": start_time.isoformat(),
            "steps": {},
            "status": "in_progress",
        }

        test_rendition = Rendition(
            title=f"[IncuBrix Cert Test] {destination.name} Verification",
            body="Automated certification test post by IncuBrix distribution harness. Will be cleaned up immediately.",
            tags=["incubrix", "test"],
            has_ai_disclosure=True,
        )

        test_post_id = None
        live_url = ""
        passed = False
        level_earned = "L0"

        try:
            # Step 1: Validate Spec
            val_res = connector.validate(test_rendition, destination, connection)
            evidence["steps"]["validate"] = {"ok": val_res.ok, "violations": val_res.violations}
            if not val_res.ok:
                raise ConnectorException("DEST_SPEC_VIOLATION", f"Validation failed: {val_res.violations}")

            # Step 2: Publish
            if destination.connector_key == "assisted":
                assist_pack = await connector.build_assist_pack(test_rendition, destination)
                pub_res = await connector.publish(test_rendition, destination, connection)
                test_post_id = pub_res.platform_post_id
                live_url = pub_res.live_url
                evidence["steps"]["publish"] = {
                    "platform_post_id": test_post_id,
                    "live_url": live_url,
                    "status": pub_res.status,
                    "assist_pack": assist_pack.model_dump(),
                }
                level_earned = "L1"
                passed = True
            else:
                pub_res = await connector.publish(test_rendition, destination, connection)
                test_post_id = pub_res.platform_post_id
                live_url = pub_res.live_url
                evidence["steps"]["publish"] = {
                    "platform_post_id": test_post_id,
                    "live_url": live_url,
                    "status": pub_res.status,
                }

                # Step 3: Get Status
                status_res = await connector.get_status(test_post_id, connection)
                evidence["steps"]["get_status"] = {
                    "status": status_res.status,
                    "live_url": status_res.live_url,
                }
                if status_res.status not in ("active", "published", "ready_for_manual_post"):
                    raise ConnectorException("PLATFORM_CONTENT_REJECTED", f"Status returned unexpected: {status_res.status}")

                # Step 4: Optional Metrics Check (to qualify for L4)
                has_metrics = False
                if "metrics" in connector.manifest.get("capabilities", []):
                    try:
                        metrics_res = await connector.fetch_metrics(test_post_id, connection)
                        evidence["steps"]["metrics"] = metrics_res.model_dump()
                        has_metrics = True
                    except Exception as e:
                        evidence["steps"]["metrics"] = {"error": str(e)}

                # Step 5: Clean up / Delete (Never spam, deleted immediately)
                del_res = await connector.delete(test_post_id, connection)
                evidence["steps"]["delete"] = {"deleted": del_res.deleted}
                if not del_res.deleted:
                    logger.warning(f"Failed to confirm post deletion for {test_post_id}")

                passed = True
                level_earned = "L4" if has_metrics else "L3"

        except Exception as e:
            passed = False
            level_earned = "L0"
            evidence["status"] = "failed"
            evidence["error"] = str(e)
            logger.error(f"Certification failed for destination {destination.name}: {e}")

        finish_time = datetime.now(timezone.utc)
        evidence["finished_at"] = finish_time.isoformat()
        evidence["duration_seconds"] = (finish_time - start_time).total_seconds()
        evidence["status"] = "passed" if passed else "failed"
        evidence["level_assigned"] = level_earned

        # Persist certification record
        with get_db() as conn:
            cur = conn.execute(
                "SELECT id FROM destinations WHERE (id = ? AND id IS NOT NULL) OR (url = ? AND platform_key = ?)",
                (destination.id, destination.url, destination.platform_key),
            )
            existing_row = cur.fetchone()
            if existing_row:
                dest_id = existing_row[0]
            else:
                dest_id = destination.id or str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO destinations (
                        id, name, url, platform_key, surface, category, audience_tags, language,
                        geo, est_audience, rules_url, frequency_cap, self_promo_allowed, link_policy,
                        disclosure_required, automation_allowed, connector_key, relevance_score,
                        relevance_reason, level, last_certified_at, config_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, '[]', 'en', 'global', 1000, '', '1/7d', 1, 'allowed', 0, 1, ?, 3, '', ?, ?, '{}', ?, ?)
                    """,
                    (
                        dest_id,
                        destination.name,
                        destination.url,
                        destination.platform_key,
                        destination.surface,
                        destination.category,
                        destination.connector_key,
                        level_earned,
                        finish_time.isoformat(),
                        finish_time.isoformat(),
                        finish_time.isoformat(),
                    ),
                )

            conn.execute(
                """
                INSERT INTO certifications (id, destination_id, connector_key, status, test_post_id, live_url, evidence_json, certified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cert_id,
                    dest_id,
                    destination.connector_key,
                    evidence["status"],
                    test_post_id,
                    live_url,
                    json.dumps(evidence),
                    finish_time.isoformat(),
                ),
            )
            # Update destination level and last_certified_at
            conn.execute(
                """
                UPDATE destinations
                SET level = ?, last_certified_at = ?, updated_at = ?
                WHERE id = ? OR name = ?
                """,
                (level_earned, finish_time.isoformat(), finish_time.isoformat(), destination.id, destination.name),
            )

        # Store evidence file in certification_pack
        out_sub_dir = self.pack_dir / destination.connector_key
        out_sub_dir.mkdir(parents=True, exist_ok=True)
        safe_name = destination.name.lower().replace(" ", "_").replace("/", "_")
        out_file = out_sub_dir / f"cert_{safe_name}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(evidence, f, indent=2)

        return evidence


certification_harness = CertificationHarness()
