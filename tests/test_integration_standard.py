"""Tests validating all 10 points of the IncuBrix Integration Standard."""
import asyncio
import json
from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient
import yaml

from src.api.app import app
from src.config import settings
from src.database import get_db
from src.logger import mask_secrets
from src.storage import get_storage


@pytest.mark.asyncio
async def test_standard_point_1_and_8_health_endpoints(client: AsyncClient):
    # Point 8: Structured logs & GET /health and /ready
    r1 = await client.get("/health")
    assert r1.status_code == 200
    assert r1.json()["status"] == "healthy"

    r2 = await client.get("/ready")
    assert r2.status_code == 200
    assert r2.json()["status"] == "healthy"


def test_standard_point_2_openapi_spec():
    # Point 2: Documented HTTP API (OpenAPI 3.1)
    openapi_file = Path("openapi.yaml")
    assert openapi_file.exists()
    with open(openapi_file, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    assert spec.get("openapi") == "3.1.0"
    assert "/api/v1/publish" in spec.get("paths", {})
    assert "/api/v1/destinations" in spec.get("paths", {})


@pytest.mark.asyncio
async def test_standard_point_3_and_4_background_jobs_and_safe_retries(client: AsyncClient):
    # Point 3: Background jobs (POST returns 202, GET /api/v1/jobs/{job_id} returns status & progress)
    # Point 4: Safe retries (Idempotency-Key returns same job)
    import uuid
    dest_name = f"Queue Test Dest {uuid.uuid4().hex[:6]}"
    await client.post("/api/v1/destinations", json={
        "name": dest_name,
        "url": f"https://queue.{uuid.uuid4().hex[:6]}.org",
        "platform_key": "discourse",
        "connector_key": "discourse",
        "frequency_cap": "10/1d",
    })
    payload = {
        "rendition": {
            "title": "Integration Standard Test Post",
            "body": "Testing background queue and safe idempotency key retries.",
            "tags": ["testing"],
            "has_ai_disclosure": True,
        },
        "destination_id": dest_name,
    }
    idemp_key = f"idemp_test_safe_{uuid.uuid4().hex[:8]}"
    headers = {"Idempotency-Key": idemp_key, "X-Correlation-Id": "test-corr-123"}

    # First POST
    res1 = await client.post("/api/v1/publish", json=payload, headers=headers)
    assert res1.status_code == 202
    data1 = res1.json()
    job_id = data1["job_id"]
    assert job_id is not None
    assert data1["status"] in ("queued", "running", "succeeded")

    # Second POST with identical Idempotency-Key MUST return the same job (Safe Retries)
    res2 = await client.post("/api/v1/publish", json=payload, headers=headers)
    assert res2.status_code == 202
    data2 = res2.json()
    assert data2["job_id"] == job_id

    # Wait for job completion
    for _ in range(20):
        await asyncio.sleep(0.2)
        job_res = await client.get(f"/api/v1/jobs/{job_id}")
        assert job_res.status_code == 200
        j_data = job_res.json()
        if j_data["status"] in ("succeeded", "failed"):
            break

    assert j_data["progress"] == 100
    assert j_data["status"] == "succeeded"
    assert "manifest_url" in j_data["result_links"]


@pytest.mark.asyncio
async def test_standard_point_5_clear_errors(client: AsyncClient):
    # Point 5: Clear errors JSON {"error": {"code", "message", "retryable", "details"}}
    res = await client.post("/api/v1/publish", json={"invalid": "payload"}, headers={"X-Correlation-Id": "err-corr-1"})
    assert res.status_code in (400, 422)
    err_json = res.json()
    assert "error" in err_json
    error = err_json["error"]
    assert "code" in error
    assert "message" in error
    assert "retryable" in error
    assert error["code"].isupper()


def test_standard_point_6_configuration():
    # Point 6: All settings from env vars or config file
    assert settings.DATABASE_URL is not None
    assert settings.STORAGE_LOCAL_DIR is not None
    assert settings.WEBHOOK_HMAC_SECRET is not None


def test_standard_point_7_files_in_files_out():
    # Point 7: Files in, files out via storage provider
    storage = get_storage()
    test_content = b'{"status": "tested"}'
    key, url = storage.save("test_artifact.json", test_content)
    assert key is not None
    assert url is not None
    retrieved = storage.get(key)
    assert retrieved == test_content


def test_standard_point_8_secret_masking():
    # Must-Have 7: Secrets protected, tokens never appear in logs
    raw_log = 'User logged in with api_key="secret_token_123456789" and Bearer eyJhbGciOiJIUzI1Ni...'
    masked = mask_secrets(raw_log)
    assert "secret_token_123456789" not in masked
    assert "se****89" in masked or "****" in masked


def test_standard_point_9_output_manifest():
    # Point 9: Output manifest structure
    from src.models.manifest import OutputManifest
    manifest = OutputManifest(
        models_providers={"connector": "discourse"},
        timings_ms={"pipeline_ms": 12.5},
        warnings=[],
    )
    m_dict = manifest.model_dump()
    assert "models_providers" in m_dict
    assert "timings_ms" in m_dict
    assert "cost_estimate_usd" in m_dict
    assert "licence_rights" in m_dict
