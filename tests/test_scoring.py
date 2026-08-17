from affiliate_intel.models import AffiliateProgram
from affiliate_intel.scanner import normalize_candidates
from affiliate_intel.scoring import score_program


def test_verified_program_scores_higher_than_same_unverified_program():
    base = dict(
        slug="example",
        name="Example",
        product_url="https://example.com",
        commission_type="recurring",
        commission_rate_pct=30,
        lifetime_recurring=True,
        cookie_days=90,
        monthly_price_from=100,
        niche_fit=0.9,
        conversion_confidence=0.7,
        competition_penalty=0.4,
        approval_friction=0.2,
    )
    verified = AffiliateProgram(**base, verification_status="verified")
    unverified = AffiliateProgram(**base, verification_status="unverified")

    assert score_program(verified).total > score_program(unverified).total


def test_rejected_program_scores_zero():
    program = AffiliateProgram(
        slug="rejected",
        name="Rejected",
        product_url="https://example.com",
        verification_status="rejected",
    )
    assert score_program(program).total == 0


def test_normalizer_deduplicates_slugs():
    programs = [
        AffiliateProgram(slug=" Tool A ", name="Tool A", product_url="https://a.example"),
        AffiliateProgram(slug="tool-a", name="Tool A duplicate", product_url="https://b.example"),
    ]
    normalized = normalize_candidates(programs)
    assert len(normalized) == 1
    assert normalized[0].slug == "tool-a"
