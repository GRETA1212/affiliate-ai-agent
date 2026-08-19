from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class Opportunity:
    name: str
    niche: str
    offer_type: str
    price: float
    commission_rate: float
    demand: float
    competition: float
    conversion_potential: float
    content_potential: float
    recurring_revenue: float
    source: str = "seed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
