"""Tests for stand-out quirks & features: Dry-run shadow pipeline, risk score meter, circuit breaker, and UI."""
import pytest
from httpx import AsyncClient
from src.connectors.registry import registry
from src.engine.rules_engine import rules_engine
from src.models.connector import Destination, Rendition


@pytest.mark.asyncio
async def test_ui_serves_html_dashboard(client: AsyncClient):
    """Verifies that GET / and GET /ui serve the glassmorphic command center HTML."""
    res_root = await client.get("/")
    assert res_root.status_code == 200
    assert "IncuBrix 2027" in res_root.text
    assert "Long-Tail Destination Network Command Center" in res_root.text

    res_ui = await client.get("/ui")
    assert res_ui.status_code == 200
    assert "Command Center" in res_ui.text


@pytest.mark.asyncio
async def test_publish_dry_run_shadow_pipeline(client: AsyncClient):
    """Verifies dry-run shadow pipeline preview without mutating database or dispatching network calls."""
    payload = {
        "destination_id": "discourse-dev-forum",
        "rendition": {
            "title": "Scaling Async Workers",
            "body": "How does your team handle worker concurrency? Check out this post.",
            "tags": ["python", "scaling"],
            "is_promotional": False,
            "has_ai_disclosure": True,
        }
    }
    resp = await client.post("/api/v1/publish/dry-run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["dry_run"] is True
    assert data["rules_check"]["passed"] is True
    assert "brand_safety_risk" in data
    assert "tailored_rendition" in data
    assert data["estimated_pipeline_ms"] >= 0.0


def test_brand_safety_risk_meter():
    """Verifies continuous risk score calculation (0-100) and grade assignment."""
    clean_rendition = Rendition(
        title="Technical Architectural Review of Message Queues",
        body="We evaluated Kafka versus RabbitMQ for asynchronous telemetry processing. Key findings below.",
        tags=["architecture", "backend"],
        is_promotional=False,
        has_ai_disclosure=True,
    )
    clean_eval = rules_engine.calculate_ban_risk_score(clean_rendition)
    assert clean_eval["risk_score"] <= 20
    assert "A" in clean_eval["safety_grade"]

    spam_rendition = Rendition(
        title="BUY NOW 50% DISCOUNT EXCLUSIVE DEAL SIGN UP TODAY",
        body="Limited offer! Click here: https://link1.com https://link2.com https://link3.com https://link4.com https://link5.com",
        tags=["promo"],
        is_promotional=True,
        has_ai_disclosure=False,
    )
    no_promo_dest = Destination(
        id="strict-dest",
        name="Strict Forum",
        url="https://strict.example.com",
        platform_key="discourse",
        connector_key="discourse",
        self_promo_allowed=False,
    )
    spam_eval = rules_engine.calculate_ban_risk_score(spam_rendition, no_promo_dest)
    assert spam_eval["risk_score"] >= 75
    assert spam_eval["level_color"] == "rose"
    assert len(spam_eval["factors"]) > 0


@pytest.mark.asyncio
async def test_circuit_breaker_and_reset(client: AsyncClient):
    """Verifies that repeated connector failures trip the circuit breaker and reset restores it."""
    test_key = "discourse"
    registry.reset_circuit_breaker(test_key)
    assert registry.is_circuit_open(test_key) is False

    # Simulate 3 consecutive failures
    registry.record_failure(test_key, "PLATFORM_429_RATE_LIMIT")
    registry.record_failure(test_key, "PLATFORM_429_RATE_LIMIT")
    registry.record_failure(test_key, "PLATFORM_500_SERVER_ERROR")

    assert registry.is_circuit_open(test_key) is True

    # Check circuit-breakers API endpoint
    cb_resp = await client.get("/api/v1/circuit-breakers")
    assert cb_resp.status_code == 200
    cb_data = cb_resp.json()
    assert cb_data[test_key]["status"] == "open"
    assert cb_data[test_key]["failures"] == 3

    # Reset circuit breaker via API
    reset_resp = await client.post(f"/api/v1/circuit-breakers/{test_key}/reset")
    assert reset_resp.status_code == 200
    assert registry.is_circuit_open(test_key) is False


@pytest.mark.asyncio
async def test_kill_switch_toggle_api(client: AsyncClient):
    """Verifies runtime operational kill-switch toggling via API."""
    test_key = "lemmy"
    # Toggle off
    res_off = await client.post(f"/api/v1/connectors/{test_key}/toggle?disabled=true")
    assert res_off.status_code == 200
    assert registry.is_disabled(test_key) is True

    # Toggle on
    res_on = await client.post(f"/api/v1/connectors/{test_key}/toggle?disabled=false")
    assert res_on.status_code == 200
    assert registry.is_disabled(test_key) is False


@pytest.mark.asyncio
async def test_precision_benchmark_endpoint(client: AsyncClient):
    """Verifies the live Precision@10 evaluator endpoint."""
    res = await client.get("/api/v1/benchmark/precision")
    assert res.status_code == 200
    data = res.json()
    assert data["k"] == 10
    assert data["samples_count"] == 3
    assert "precision_percentage" in data
