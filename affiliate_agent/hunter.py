from __future__ import annotations

from .models import Opportunity
from .scorer import score_opportunity


SEED_OPPORTUNITIES = [
    Opportunity("AI meeting notes", "AI productivity", "SaaS", 24, 0.30, 88, 64, 78, 90, 95),
    Opportunity("AI resume builder", "Career", "SaaS", 29, 0.35, 84, 68, 82, 92, 80),
    Opportunity("AI video editor", "Creator tools", "SaaS", 39, 0.30, 91, 74, 76, 96, 90),
    Opportunity("Website builder", "Small business", "SaaS", 49, 0.40, 87, 72, 79, 88, 92),
    Opportunity("Email marketing platform", "Marketing", "SaaS", 59, 0.30, 82, 70, 83, 82, 96),
    Opportunity("AI study assistant", "Education", "SaaS", 19, 0.30, 90, 67, 80, 95, 85),
    Opportunity("Language learning app", "Education", "App", 15, 0.25, 89, 76, 75, 90, 88),
    Opportunity("VPN subscription", "Privacy", "SaaS", 60, 0.40, 86, 78, 84, 80, 94),
    Opportunity("Cloud storage", "Productivity", "SaaS", 30, 0.25, 83, 73, 82, 76, 94),
    Opportunity("Password manager", "Security", "SaaS", 36, 0.30, 81, 69, 86, 74, 94),
    Opportunity("AI coding assistant", "Developer tools", "SaaS", 20, 0.25, 92, 82, 78, 91, 91),
    Opportunity("No-code automation", "Automation", "SaaS", 35, 0.35, 85, 66, 79, 93, 96),
    Opportunity("Online course platform", "Creator economy", "SaaS", 69, 0.30, 79, 61, 76, 84, 97),
    Opportunity("Print-on-demand platform", "Ecommerce", "Platform", 0, 0.00, 75, 65, 70, 86, 40),
    Opportunity("Domain and hosting", "Web", "SaaS", 48, 0.45, 88, 80, 81, 84, 75),
    Opportunity("AI presentation maker", "Business", "SaaS", 20, 0.30, 84, 62, 79, 92, 87),
    Opportunity("Social media scheduler", "Marketing", "SaaS", 30, 0.30, 78, 64, 81, 85, 95),
    Opportunity("Stock media subscription", "Creators", "SaaS", 29, 0.25, 76, 58, 74, 89, 88),
    Opportunity("Digital design templates", "Design", "Digital product", 27, 0.50, 80, 57, 85, 94, 35),
    Opportunity("AI transcription", "Productivity", "SaaS", 18, 0.30, 83, 60, 82, 88, 92),
]


def find_opportunities(limit: int = 20) -> list[Opportunity]:
    return SEED_OPPORTUNITIES[: max(1, limit)]


def rank_opportunities(limit: int = 20) -> list[tuple[Opportunity, float]]:
    ranked = [(item, score_opportunity(item)) for item in find_opportunities(limit)]
    return sorted(ranked, key=lambda pair: pair[1], reverse=True)


def top_opportunities(top_n: int = 3, limit: int = 20) -> list[tuple[Opportunity, float]]:
    return rank_opportunities(limit)[: max(1, top_n)]
