"""Tests validating exact connector contract conforming to Appendix A."""
import pytest
from src.connectors.base import ConnectorException
from src.connectors.registry import registry
from src.models.connector import Connection, Destination, Rendition


@pytest.mark.asyncio
async def test_all_connectors_registered():
    expected_connectors = ["discourse", "lemmy", "devto", "ghost", "webhook", "assisted", "hashnode", "slack", "mrss"]
    for key in expected_connectors:
        conn = registry.get(key)
        assert conn is not None
        assert conn.key == key
        assert conn.manifest is not None
        assert "tier" in conn.manifest
        assert "capabilities" in conn.manifest


@pytest.mark.asyncio
async def test_connector_spec_validation():
    discourse = registry.get("discourse")
    dest = Destination(
        name="Test Discourse",
        url="https://discourse.example.com",
        platform_key="discourse",
        connector_key="discourse",
    )
    conn = Connection()

    # Normal rendition
    good_rendition = Rendition(
        title="Valid Title",
        body="Valid body content under 32k chars.",
    )
    val = discourse.validate(good_rendition, dest, conn)
    assert val.ok is True
    assert len(val.violations) == 0

    # Oversized title breaking format limits
    long_title = "X" * 300
    bad_rendition = Rendition(title=long_title, body="Short body")
    val_bad = discourse.validate(bad_rendition, dest, conn)
    assert val_bad.ok is False
    assert any("Title length" in v for v in val_bad.violations)


@pytest.mark.asyncio
async def test_core_connectors_contract_methods():
    core_keys = ["discourse", "lemmy", "devto", "ghost", "webhook"]
    for key in core_keys:
        connector = registry.get(key)
        dest = Destination(
            name=f"Test {key}",
            url=f"https://{key}.example.com",
            platform_key=key,
            connector_key=key,
        )
        conn = Connection()
        rendition = Rendition(
            title="Contract Test Title",
            body="Contract test body content.",
            tags=["test"],
        )

        # 1. Publish
        pub_res = await connector.publish(rendition, dest, conn, idempotency_key=f"idemp_{key}_1")
        assert pub_res.platform_post_id != ""
        assert pub_res.live_url != ""
        assert pub_res.status == "published"

        # 2. Get Status
        status_res = await connector.get_status(pub_res.platform_post_id, conn)
        assert status_res.status in ("active", "published")

        # 3. Delete
        del_res = await connector.delete(pub_res.platform_post_id, conn)
        assert del_res.deleted is True


@pytest.mark.asyncio
async def test_assisted_connector_pack():
    assisted = registry.get("assisted")
    dest = Destination(
        name="Manual Subreddit",
        url="https://reddit.com/r/SaaS",
        platform_key="assisted",
        connector_key="assisted",
        self_promo_allowed=False,
        disclosure_required=True,
    )
    rendition = Rendition(
        title="Case Study: How We Built PS4",
        body="Detailed insights on engineering a long-tail distribution network.",
        has_ai_disclosure=True,
        tags=["engineering", "saas"],
    )

    pack = await assisted.build_assist_pack(rendition, dest)
    assert pack.caption is not None
    assert "Case Study" in pack.caption
    assert pack.deep_link.endswith("/submit")
    assert any("AI generation disclosure" in item for item in pack.checklist)
    assert any("DO NOT include direct promotional" in item for item in pack.checklist)


@pytest.mark.asyncio
async def test_kill_switch_connector_disabled():
    registry.set_disabled("slack", True)
    with pytest.raises(ConnectorException) as exc_info:
        registry.get("slack")
    assert exc_info.value.code == "CONNECTOR_DISABLED"
    registry.set_disabled("slack", False)
    assert registry.get("slack") is not None
