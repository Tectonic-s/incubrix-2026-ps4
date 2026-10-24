"""Tests validating posting-rules engine policies (Must-Have 4 & Hard Case 4)."""
import uuid
from datetime import datetime, timezone
import pytest
from src.connectors.base import ConnectorException
from src.database import get_db
from src.engine.rules_engine import rules_engine
from src.models.connector import Destination, Rendition


def test_frequency_cap_blocking_second_post():
    dest_id = f"dest_freq_{uuid.uuid4().hex[:6]}"
    dest = Destination(
        id=dest_id,
        name="Weekly Cap Forum",
        url=f"https://forum.testcap_{dest_id}.org",
        platform_key="discourse",
        connector_key="discourse",
        frequency_cap="1/7d",
    )

    rendition = Rendition(title="First Post", body="Original valuable post content")

    # Initial check passes
    res = rules_engine.check_rules(rendition, dest)
    assert res["valid"] is True

    # Record first post in database
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO destinations (id, name, url, platform_key, connector_key, frequency_cap, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (dest_id, dest.name, dest.url, dest.platform_key, dest.connector_key, dest.frequency_cap, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
        )
        conn.execute(
            """
            INSERT INTO posts (id, destination_id, platform_post_id, status, title, rendition_json, published_at)
            VALUES (?, ?, 'post_01', 'published', ?, '{}', ?)
            """,
            (str(uuid.uuid4()), dest_id, rendition.title, datetime.now(timezone.utc).isoformat()),
        )

    # Second post within weekly cap MUST raise DEST_RULE_FREQUENCY_CAP with reschedule details
    second_rendition = Rendition(title="Second Post Soon", body="Another post within the 7-day window")
    with pytest.raises(ConnectorException) as exc_info:
        rules_engine.check_rules(second_rendition, dest)

    assert exc_info.value.code == "DEST_RULE_FREQUENCY_CAP"
    assert exc_info.value.retryable is True
    assert "Frequency cap reached" in exc_info.value.message
    assert "reschedule_at" in exc_info.value.details


def test_self_promotion_policy_blocking():
    dest = Destination(
        name="Strict No-Promo Community",
        url="https://community.nopromo.org",
        platform_key="lemmy",
        connector_key="lemmy",
        self_promo_allowed=False,
    )

    promo_rendition = Rendition(
        title="Check out our SaaS - Buy now with 50% off discount!",
        body="Limited offer special deal, sign up today at our site.",
        is_promotional=True,
    )

    with pytest.raises(ConnectorException) as exc_info:
        rules_engine.check_rules(promo_rendition, dest)

    assert exc_info.value.code == "DEST_SPEC_VIOLATION"
    assert "Destination strictly bans self-promotion" in str(exc_info.value.details["violations"])


def test_link_policy_blocking_affiliates():
    dest = Destination(
        name="No Affiliate Hub",
        url="https://hub.noaffiliate.org",
        platform_key="discourse",
        connector_key="discourse",
        link_policy="no_affiliate",
    )

    affiliate_rendition = Rendition(
        title="Great dev tool roundup",
        body="Check out this tool at https://example.com/tool?ref=my_affiliate_id for a discount.",
    )

    with pytest.raises(ConnectorException) as exc_info:
        rules_engine.check_rules(affiliate_rendition, dest)

    assert exc_info.value.code == "DEST_SPEC_VIOLATION"
    assert any("prohibited" in v for v in exc_info.value.details["violations"])


def test_ai_disclosure_requirement():
    dest = Destination(
        name="AI Transparency Forum",
        url="https://forum.aitransparent.org",
        platform_key="discourse",
        connector_key="discourse",
        disclosure_required=True,
    )

    undisclosed_rendition = Rendition(
        title="Article without AI notice",
        body="This text contains zero disclosure statement.",
        has_ai_disclosure=False,
    )

    with pytest.raises(ConnectorException) as exc_info:
        rules_engine.check_rules(undisclosed_rendition, dest)

    assert exc_info.value.code == "DEST_SPEC_VIOLATION"
    assert any("disclosure" in v for v in exc_info.value.details["violations"])
