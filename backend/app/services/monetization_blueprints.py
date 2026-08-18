from pydantic import BaseModel, Field


class ContentAngle(BaseModel):
    title: str
    intent: str
    channel: str
    cta: str


class MonetizationBlueprint(BaseModel):
    advertiser: str
    product_name: str
    priority: int = Field(ge=1)
    target_audience: str
    problem: str
    primary_goal: str
    tracking_source: str
    content_angles: list[ContentAngle]
    compliance_notes: list[str] = Field(default_factory=list)


BLUEPRINTS: tuple[MonetizationBlueprint, ...] = (
    MonetizationBlueprint(
        advertiser="Hostinger",
        product_name="Hostinger Horizons",
        priority=1,
        target_audience=(
            "Founders, freelancers and small businesses that want to build and publish "
            "AI-assisted web apps without managing a traditional development stack."
        ),
        problem=(
            "The buyer wants to launch an app quickly but is comparing AI app builders, "
            "hosting requirements, pricing and ease of deployment."
        ),
        primary_goal="Generate qualified affiliate clicks that can convert into eligible Horizons purchases.",
        tracking_source="hostinger-horizons",
        content_angles=[
            ContentAngle(
                title="Hostinger Horizons review: who should use it and who should not",
                intent="commercial investigation",
                channel="seo_article",
                cta="Try Hostinger Horizons through the tracked affiliate link.",
            ),
            ContentAngle(
                title="Hostinger Horizons vs Lovable: which AI app builder is better for a small business?",
                intent="comparison",
                channel="seo_article",
                cta="Compare the workflows, then use the tracked link for the best-fit option.",
            ),
            ContentAngle(
                title="How to build and publish a simple business app with Hostinger Horizons",
                intent="tutorial",
                channel="youtube_or_article",
                cta="Follow the tutorial and open Horizons through the tracked link.",
            ),
            ContentAngle(
                title="Best AI app builders for non-developers",
                intent="high-intent list",
                channel="seo_article",
                cta="Choose the recommended tool using a clearly disclosed tracked link.",
            ),
        ],
        compliance_notes=[
            "Disclose the affiliate relationship clearly before or near affiliate links.",
            "Do not self-refer, force cookies, cloak traffic sources, or use spam/black-hat promotion.",
            "Do not claim a guaranteed commission rate; describe the public offer as up to 60% where applicable.",
            "Use approved Hostinger promotional assets when using Hostinger-branded creative.",
        ],
    ),
    MonetizationBlueprint(
        advertiser="Semrush",
        product_name="Semrush",
        priority=2,
        target_audience=(
            "Website owners, agencies, marketers and AI-search/SEO practitioners who need "
            "visibility, keyword, competitor and AI-search measurement tools."
        ),
        problem=(
            "The buyer wants measurable search or AI visibility growth and is comparing SEO/AI visibility platforms."
        ),
        primary_goal="Generate trial activations and qualified first-purchase referrals.",
        tracking_source="semrush",
        content_angles=[
            ContentAngle(
                title="Semrush review for AI visibility and SEO in 2026",
                intent="commercial investigation",
                channel="seo_article",
                cta="Start with the tracked Semrush trial or product link.",
            ),
            ContentAngle(
                title="Semrush vs Ahrefs for SEO and AI visibility",
                intent="comparison",
                channel="seo_article",
                cta="Choose the best-fit platform through the disclosed tracked link.",
            ),
            ContentAngle(
                title="How to measure whether ChatGPT and AI search engines can see your brand",
                intent="tutorial",
                channel="youtube_or_article",
                cta="Use Semrush to reproduce the workflow through the tracked link.",
            ),
        ],
        compliance_notes=[
            "Disclose affiliate links and avoid fabricated results or testimonials.",
            "Do not state the maximum payout as guaranteed; payout depends on product and partner tier.",
            "Measure trial and sale conversions separately because the program can reward both.",
        ],
    ),
)


def list_blueprints() -> list[MonetizationBlueprint]:
    return sorted(BLUEPRINTS, key=lambda item: item.priority)


def get_blueprint(advertiser: str) -> MonetizationBlueprint | None:
    normalized = advertiser.strip().lower()
    for blueprint in BLUEPRINTS:
        if blueprint.advertiser.lower() == normalized or blueprint.product_name.lower() == normalized:
            return blueprint
    return None
