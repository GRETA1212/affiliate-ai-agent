from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

VerificationStatus = Literal["unverified", "verified", "stale", "rejected"]
CommissionType = Literal["recurring", "one_time", "hybrid", "unknown"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class AffiliateProgram:
    slug: str
    name: str
    product_url: str
    affiliate_url: str | None = None
    commission_type: CommissionType = "unknown"
    commission_rate_pct: float | None = None
    commission_amount: float | None = None
    recurring_months: int | None = None
    lifetime_recurring: bool = False
    cookie_days: int | None = None
    monthly_price_from: float | None = None
    monthly_price_to: float | None = None
    niche_fit: float = 0.5
    conversion_confidence: float = 0.5
    competition_penalty: float = 0.5
    approval_friction: float = 0.5
    verification_status: VerificationStatus = "unverified"
    source_url: str | None = None
    source_checked_at: str | None = None
    notes: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def validate(self) -> None:
        for field_name in (
            "niche_fit",
            "conversion_confidence",
            "competition_penalty",
            "approval_friction",
        ):
            value = getattr(self, field_name)
            if not 0 <= value <= 1:
                raise ValueError(f"{field_name} must be between 0 and 1")
        if self.commission_rate_pct is not None and self.commission_rate_pct < 0:
            raise ValueError("commission_rate_pct cannot be negative")
        if self.cookie_days is not None and self.cookie_days < 0:
            raise ValueError("cookie_days cannot be negative")


@dataclass(slots=True, frozen=True)
class ScoreBreakdown:
    total: float
    economics: float
    attribution: float
    fit: float
    conversion: float
    competition: float
    friction: float
    verification_multiplier: float
