from affiliate_agent.hunter import rank_opportunities, top_opportunities
from affiliate_agent.models import Opportunity
from affiliate_agent.scorer import score_opportunity


def test_score_is_bounded() -> None:
    item = Opportunity("x", "test", "SaaS", 50, 0.4, 120, -10, 80, 90, 100)
    score = score_opportunity(item)
    assert 0 <= score <= 100


def test_rank_returns_twenty() -> None:
    ranked = rank_opportunities(20)
    assert len(ranked) == 20
    assert ranked == sorted(ranked, key=lambda pair: pair[1], reverse=True)


def test_top_three() -> None:
    assert len(top_opportunities(3, 20)) == 3
