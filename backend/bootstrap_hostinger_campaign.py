import os

from app.services import campaign_workspace as workspace

SLUG = "hostinger-horizons"


def main() -> None:
    affiliate_url = os.getenv("HOSTINGER_HORIZONS_AFFILIATE_URL", "").strip()
    tracking_base_url = os.getenv("AFFILIATE_TRACKING_BASE_URL", "").rstrip("/")

    if not affiliate_url:
        raise SystemExit(
            "HOSTINGER_HORIZONS_AFFILIATE_URL is required. "
            "Use the approved Hostinger affiliate URL, not a generic product URL."
        )

    existing = next(
        (item for item in workspace.list_campaigns() if item.campaign.slug == SLUG),
        None,
    )

    audience = (
        "People comparing AI app builders and no-code/AI-assisted app creation tools"
    )
    problem = (
        "Choose and launch an AI-built web app with an integrated hosting workflow"
    )

    if existing:
        detail = workspace.update_campaign(
            existing.campaign.id,
            workspace.CampaignUpdate(
                affiliate_url=affiliate_url,
                status="active",
                name="Hostinger Horizons",
                audience=audience,
                problem=problem,
            ),
        )
        action = "updated"
    else:
        detail = workspace.create_campaign(
            workspace.CampaignCreate(
                name="Hostinger Horizons",
                product_name="Hostinger Horizons",
                audience=audience,
                problem=problem,
                affiliate_url=affiliate_url,
                slug=SLUG,
                status="active",
                source="hostinger-direct",
                opportunity_score=95,
            )
        )
        action = "created"

    print(f"Campaign {action}: {detail.campaign.id}")
    print(f"Slug: {detail.campaign.slug}")
    if tracking_base_url:
        print(f"Tracked URL: {tracking_base_url}/go/{SLUG}")
    else:
        print(f"Tracked path: /go/{SLUG}")


if __name__ == "__main__":
    main()
