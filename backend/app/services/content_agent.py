from app.models import CampaignPlan, CampaignRequest


def build_campaign(request: CampaignRequest) -> CampaignPlan:
    product = request.product_name.strip()
    audience = request.audience.strip()
    problem = request.problem.strip()
    angle = f"Help {audience} solve {problem} and introduce {product} only where it genuinely fits."
    return CampaignPlan(
        angle=angle,
        article_titles=[
            f"How to Solve {problem.title()}: A Practical Guide for {audience.title()}",
            f"{product} Review: Pros, Cons, and Who It Is For",
            f"{product} Alternatives: What {audience.title()} Should Compare",
        ],
        video_titles=[
            f"I Tried {product}: What {audience.title()} Should Know",
            f"How to Fix {problem.title()} Step by Step",
            f"{product} vs Alternatives: Which Fits Your Use Case?",
        ],
        disclosure=(
            "Disclosure: This content may contain affiliate links. If you purchase through one, "
            "the publisher may earn a commission at no additional cost to you."
        ),
        affiliate_url=request.affiliate_url,
    )
