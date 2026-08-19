"""Affiliate AI opportunity hunter."""

from .models import Opportunity
from .scorer import score_opportunity

__all__ = ["Opportunity", "score_opportunity"]
