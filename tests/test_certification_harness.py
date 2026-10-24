"""Tests validating certification harness and schema drift detection (Must-Have 2 & Hard Case 5)."""
from pathlib import Path
import pytest
from src.database import get_db
from src.engine.certification import certification_harness
from src.models.connector import Connection, Destination


@pytest.mark.asyncio
async def test_certify_discourse_destination():
    dest = Destination(
        id="dest_cert_disc_01",
        name="Discourse Certification Instance",
        url="https://discourse.example.com",
        platform_key="discourse",
        connector_key="discourse",
    )
    conn = Connection()

    evidence = await certification_harness.certify_destination(dest, conn)

    assert evidence["status"] == "passed"
    assert evidence["level_assigned"] in ("L3", "L4")
    assert "publish" in evidence["steps"]
    assert "get_status" in evidence["steps"]
    assert "delete" in evidence["steps"]
    assert evidence["steps"]["delete"]["deleted"] is True

    # Check evidence file persisted
    evidence_file = Path(f"./certification_pack/discourse/cert_{dest.name.lower().replace(' ', '_')}.json")
    assert evidence_file.exists()


@pytest.mark.asyncio
async def test_certify_assisted_destination():
    dest = Destination(
        id="dest_cert_assist_01",
        name="Assisted Forum Test",
        url="https://reddit.com/r/SaaS",
        platform_key="assisted",
        connector_key="assisted",
    )
    conn = Connection()

    evidence = await certification_harness.certify_destination(dest, conn)

    assert evidence["status"] == "passed"
    assert evidence["level_assigned"] == "L1"
    assert "assist_pack" in evidence["steps"]["publish"]


@pytest.mark.asyncio
async def test_schema_drift_fails_certification_and_demotes():
    # Destination that encounters schema drift (missing expected id in response)
    dest = Destination(
        id="dest_drift_01",
        name="Schema Drift Forum",
        url="http://mock-drift.test",
        platform_key="discourse",
        connector_key="discourse",
        level="L3",
    )
    conn = Connection(base_url="http://invalid-endpoint-causing-failure")

    evidence = await certification_harness.certify_destination(dest, conn)

    assert evidence["status"] == "failed"
    assert evidence["level_assigned"] == "L0"
    assert "error" in evidence
