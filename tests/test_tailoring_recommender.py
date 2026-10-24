"""Tests validating tailoring, AI rules capture, recommendation ranking, and recertification."""
import json
from pathlib import Path
import pytest
from src.database import get_db
from src.engine.recertification import recertification_scheduler
from src.engine.recommender import recommendation_engine
from src.engine.rules_capture import rules_capture_engine
from src.engine.tailoring import tailoring_engine
from src.models.connector import Destination, Rendition


def test_tailoring_discussion_framing_and_word_truncation():
    dest = Destination(
        name="Tech Forum",
        url="https://forum.example.com",
        platform_key="discourse",
        connector_key="discourse",
        surface="topic",
    )
    long_title = "This is a super long announcement title that exceeds sixty characters and needs clean word-boundary truncation for community posting"
    rendition = Rendition(
        title=long_title,
        body="Short body about developer productivity.",
        tags=["Developer Tools", "AI Workflow!"],
    )

    tailored = tailoring_engine.tailor(rendition, dest)

    # Word boundary truncation
    assert len(tailored.title) <= 255
    assert not tailored.title.endswith(" truncation...")  # checks clean truncation
    # Discussion hook
    assert "Discussion Question:" in tailored.body
    # Tags formatted
    assert "developer-tools" in tailored.tags


def test_tailoring_canonical_url_for_articles():
    dest = Destination(
        name="Dev.to Hub",
        url="https://dev.to/t/ai",
        platform_key="devto",
        connector_key="devto",
        surface="article",
    )
    rendition = Rendition(
        title="Article Title",
        body="Article content.",
    )

    tailored = tailoring_engine.tailor(rendition, dest)
    assert tailored.canonical_url is not None
    assert tailored.canonical_url.startswith("http")


@pytest.mark.asyncio
async def test_ai_rules_capture_and_human_confirmation():
    rules_text = """
    Community Posting Guidelines:
    1. Only one post per month is permitted per account.
    2. Strictly no advertising or promotional sales pitches.
    3. No affiliate links allowed under any circumstance.
    4. All generative AI content must be explicitly declared and labeled.
    """
    prop = await rules_capture_engine.propose_rules("https://community.sample.org", rules_text)
    assert prop["status"] == "pending_human_review"
    assert prop["proposed_rules"]["frequency_cap"] == "1/30d"
    assert prop["proposed_rules"]["self_promo_allowed"] is False
    assert prop["proposed_rules"]["link_policy"] == "no_affiliate"
    assert prop["proposed_rules"]["disclosure_required"] is True

    # Human confirms
    conf = rules_capture_engine.confirm_rules(
        proposal_id=prop["proposal_id"],
        confirmed_rules=prop["proposed_rules"],
    )
    assert conf["status"] == "confirmed"


def test_recommender_precision_at_10():
    eval_file = Path("./data/labeled_recommendation_eval.json")
    assert eval_file.exists()
    with open(eval_file, "r", encoding="utf-8") as f:
        eval_data = json.load(f)

    metrics = recommendation_engine.evaluate_precision_at_k(eval_data, k=10)
    assert metrics["k"] == 10
    assert metrics["mean_precision_at_k"] >= 0.70
    print(f"\nRecommender Precision@10: {metrics['precision_percentage']} ({metrics['mean_precision_at_k']})")


@pytest.mark.asyncio
async def test_recertification_scheduler():
    res = await recertification_scheduler.run_recertification(force_all=True)
    assert "destinations_checked" in res
    assert "passed_count" in res
    assert "demoted_count" in res
