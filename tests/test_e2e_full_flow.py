"""Comprehensive End-to-End Test covering complete distribution pipeline (Integration Standard 1)."""
import asyncio
import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_complete_e2e_distribution_lifecycle(client: AsyncClient):
    unique_suffix = uuid.uuid4().hex[:6]
    dest_name = "E2E AI Developers Community"
    dest_url = f"https://e2e-forum-{unique_suffix}.org"

    # Step 1: Register destination configuration row (Must-Have 3)
    reg_resp = await client.post("/api/v1/destinations", json={
        "name": dest_name,
        "url": dest_url,
        "platform_key": "discourse",
        "connector_key": "discourse",
        "category": "ai",
        "audience_tags": ["ai", "developers", "llm"],
        "frequency_cap": "5/24h",
        "self_promo_allowed": True,
        "link_policy": "allowed",
        "disclosure_required": True,
        "relevance_score": 5,
        "relevance_reason": "Core AI developer community",
    })
    assert reg_resp.status_code == 200
    dest_id = reg_resp.json()["id"]

    # Step 2: AI Rules Capture & Human Confirmation (Advanced Level)
    rules_text = f"Guidelines for {dest_name}: Weekly cap 5 posts, disclose all AI content clearly, no affiliate spam."
    prop_resp = await client.post("/api/v1/rules/propose", json={
        "community_url": dest_url,
        "rules_text_or_url": rules_text,
    })
    assert prop_resp.status_code == 200
    proposal_id = prop_resp.json()["proposal_id"]

    conf_resp = await client.post("/api/v1/rules/confirm", json={
        "proposal_id": proposal_id,
        "confirmed_rules": {
            "frequency_cap": "5/24h",
            "self_promo_allowed": True,
            "link_policy": "no_affiliate",
            "disclosure_required": True,
        },
        "destination_id": dest_id,
    })
    assert conf_resp.status_code == 200
    assert conf_resp.json()["status"] == "confirmed"

    # Step 3: Run Full Certification (Must-Have 2 & Core Level)
    cert_resp = await client.post("/api/v1/certify", json={"destination_id": dest_id})
    assert cert_resp.status_code == 200
    cert_data = cert_resp.json()
    assert cert_data["status"] == "passed"
    assert cert_data["level_assigned"] in ("L3", "L4")
    assert cert_data["steps"]["delete"]["deleted"] is True

    # Step 4: Recommender Ranking (Outstanding Level)
    rendition_input = {
        "title": "Deploying Low-Latency LLM Serving Nodes with vLLM and TensorRT",
        "body": "Detailed benchmark results comparing inference throughput across tensor parallel configurations.",
        "tags": ["ai", "llm", "developers"],
        "has_ai_disclosure": True,
        "is_promotional": False,
    }
    rec_resp = await client.post("/api/v1/recommend", json={"rendition": rendition_input, "top_k": 5})
    assert rec_resp.status_code == 200
    recommendations = rec_resp.json()["recommendations"]
    assert len(recommendations) > 0
    top_dest_names = [r["destination_name"] for r in recommendations]
    assert dest_name in top_dest_names

    # Step 5: Publish via Background Job (Integration Standard 3 & Must-Have 4)
    idemp_key = f"e2e_idemp_{uuid.uuid4().hex[:10]}"
    pub_resp = await client.post(
        "/api/v1/publish",
        json={
            "rendition": rendition_input,
            "destination_id": dest_id,
        },
        headers={
            "Idempotency-Key": idemp_key,
            "X-Correlation-Id": f"corr_e2e_{unique_suffix}",
        },
    )
    assert pub_resp.status_code == 202
    job_id = pub_resp.json()["job_id"]

    # Step 6: Verify Safe Retries (Integration Standard 4)
    retry_resp = await client.post(
        "/api/v1/publish",
        json={
            "rendition": rendition_input,
            "destination_id": dest_id,
        },
        headers={"Idempotency-Key": idemp_key},
    )
    assert retry_resp.status_code == 202
    assert retry_resp.json()["job_id"] == job_id

    # Step 7: Await Background Job Execution & Verify Manifest Output (Integration Standard 9)
    final_job = None
    for _ in range(25):
        await asyncio.sleep(0.2)
        j_resp = await client.get(f"/api/v1/jobs/{job_id}")
        assert j_resp.status_code == 200
        final_job = j_resp.json()
        if final_job["status"] in ("succeeded", "failed"):
            break

    assert final_job is not None
    assert final_job["status"] == "succeeded"
    assert final_job["progress"] == 100
    assert "manifest_url" in final_job["result_links"]
    assert "live_url" in final_job["result_links"]

    # Step 8: Normalised Metrics Verification (Outstanding Level)
    metrics_resp = await client.post(
        "/connector/v1/discourse/fetch_metrics",
        json={
            "platform_post_id": final_job["result_links"]["platform_post_id"],
            "connection": {},
        },
    )
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert "views" in metrics
    assert "likes" in metrics
    assert "comments" in metrics
