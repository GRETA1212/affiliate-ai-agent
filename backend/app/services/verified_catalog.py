from datetime import date

from pydantic import BaseModel, Field


class VerifiedAffiliateProgram(BaseModel):
    name: str
    advertiser: str
    category: str
    program_url: str
    application_url: str | None = None
    network: str | None = None
    commission_text: str
    commission_percent: float | None = None
    fixed_payout_amount: float | None = None
    fixed_payout_currency: str | None = None
    cookie_days: int | None = None
    recurring: bool = False
    recurring_months: int | None = None
    verified_at: date
    tags: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


VERIFIED_PROGRAMS: tuple[VerifiedAffiliateProgram, ...] = (
    VerifiedAffiliateProgram(
        name="Semrush Affiliate Program",
        advertiser="Semrush",
        category="AI visibility and SEO",
        program_url="https://www.semrush.com/lp/affiliate-program/en/",
        network="impact",
        commission_text="Up to $450 per sale plus $10 per trial; 120-day cookie.",
        fixed_payout_amount=450.0,
        fixed_payout_currency="USD",
        cookie_days=120,
        recurring=False,
        verified_at=date(2026, 8, 12),
        tags=["ai search", "geo", "seo", "marketing", "ai visibility"],
        notes=[
            "Commission varies by product and partner tier.",
            "Published program terms use last-click attribution with a 120-day cookie window.",
        ],
    ),
    VerifiedAffiliateProgram(
        name="Lovable Affiliate Partner Program",
        advertiser="Lovable",
        category="AI app builder",
        program_url="https://lovable.dev/pt-br/partners/affiliates",
        application_url="mailto:affiliates@lovable.dev",
        network="direct",
        commission_text="Up to 20% commission on referrals for 1 year from sign-up.",
        commission_percent=20.0,
        recurring=True,
        recurring_months=12,
        verified_at=date(2026, 8, 11),
        tags=["ai app builder", "vibe coding", "developer tools", "no code"],
        notes=["Application review is required before receiving a referral link."],
    ),
    VerifiedAffiliateProgram(
        name="Hostinger Horizons Affiliate Program",
        advertiser="Hostinger",
        category="AI app builder and hosting",
        program_url="https://www.hostinger.com/horizons/affiliate-program",
        network="direct",
        commission_text="Up to 60% commission on eligible initial Horizons purchases; cookie stored for up to 30 days.",
        commission_percent=60.0,
        cookie_days=30,
        recurring=False,
        verified_at=date(2026, 8, 12),
        tags=["ai app builder", "hosting", "website builder", "vibe coding"],
        notes=[
            "Current agreement says Horizons commission applies to the initial purchase, not renewals.",
            "The up-to-60% Horizons commission is available on specific offers and is not guaranteed for every affiliate.",
            "Hostinger prohibits self-referrals, cookie insertion, spam/black-hat techniques and certain unauthorized paid advertising methods.",
        ],
    ),
    VerifiedAffiliateProgram(
        name="ElevenLabs Creator Affiliate Program",
        advertiser="ElevenLabs",
        category="AI voice",
        program_url="https://elevenlabs.io/affiliates",
        network="partnerstack",
        commission_text=(
            "22% of eligible Starter, Creator, Pro and Scale payments for 12 months; "
            "11% on Business."
        ),
        commission_percent=22.0,
        recurring=True,
        recurring_months=12,
        verified_at=date(2026, 8, 11),
        tags=["ai voice", "text to speech", "audio", "creator tools"],
        notes=["Enterprise plans are not commissionable under the published creator program."],
    ),
    VerifiedAffiliateProgram(
        name="Sintra AI Affiliate Program",
        advertiser="Sintra AI",
        category="AI business agents",
        program_url="https://help.sintra.ai/en/articles/9675436-sintra-ai-affiliate-program",
        network="impact",
        commission_text="Up to 50% on referred sales plus 15% on recurring subscriptions.",
        commission_percent=50.0,
        recurring=True,
        recurring_months=12,
        verified_at=date(2026, 8, 11),
        tags=["ai agents", "business automation", "small business", "productivity"],
        notes=["Payout processing is described as using Impact."],
    ),
)


def search_verified_programs(keywords: str | None) -> list[VerifiedAffiliateProgram]:
    if not keywords:
        return list(VERIFIED_PROGRAMS)
    tokens = [token.lower() for token in keywords.replace("/", " ").split() if len(token) >= 2]
    if not tokens:
        return list(VERIFIED_PROGRAMS)

    matches: list[VerifiedAffiliateProgram] = []
    for program in VERIFIED_PROGRAMS:
        haystack = " ".join(
            [
                program.name,
                program.advertiser,
                program.category,
                program.commission_text,
                *program.tags,
            ]
        ).lower()
        if any(token in haystack for token in tokens):
            matches.append(program)
    return matches
