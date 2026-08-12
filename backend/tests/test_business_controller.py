from pathlib import Path

import pytest

from app.services import business_controller as controller
from app.services.business_controller import (
    ContentJobCreate,
    ExpenseCreate,
    ExperimentCreate,
)
from app.services.campaign_workspace import CampaignCreate, ConversionCreate, add_conversion, create_campaign


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AFFILIATE_DB_PATH", str(tmp_path / "affiliate.db"))


def _campaign(status: str = "active"):
    return create_campaign(
        CampaignCreate(
            name="Hostinger Horizons test",
            product_name="Hostinger Horizons",
            audience="AI app builder buyers",
            problem="Choose an app builder",
            affiliate_url="https://example.com/affiliate",
            status=status,
            opportunity_score=90,
        )
    )


def test_profit_summary_subtracts_expenses() -> None:
    campaign = _campaign()
    add_conversion(
        campaign.campaign.id,
        ConversionCreate(commission_amount=100, currency="EUR", status="approved"),
    )
    controller.record_expense(ExpenseCreate(amount=25, currency="EUR", category="hosting"))

    summary = controller.profit_summary()

    assert summary.approved_revenue_by_currency["EUR"] == 100
    assert summary.expenses_by_currency["EUR"] == 25
    assert summary.profit_by_currency["EUR"] == 75


def test_job_queue_claim_and_complete() -> None:
    job_id = controller.enqueue_content_job(
        ContentJobCreate(job_type="article", title="Create buyer guide", priority=90)
    )

    job = controller.claim_next_job()

    assert job is not None
    assert job["id"] == job_id
    assert job["status"] == "running"
    controller.complete_job(job_id, {"published": False})


def test_experiment_selects_better_variant() -> None:
    campaign = _campaign()
    experiment_id = controller.create_experiment(
        ExperimentCreate(
            campaign_id=campaign.campaign.id,
            name="CTA test",
            variant_a="Try Hostinger Horizons",
            variant_b="Build your first AI app",
        )
    )
    for _ in range(50):
        controller.record_experiment_observation(experiment_id, "a", converted=False)
        controller.record_experiment_observation(experiment_id, "b", converted=True)

    assert controller.finish_experiment(experiment_id) == "b"


def test_draft_campaign_becomes_launch_action() -> None:
    campaign = _campaign(status="draft")

    actions = controller.next_actions()

    assert actions[0].campaign_id == campaign.campaign.id
    assert actions[0].action == "prepare-launch"
