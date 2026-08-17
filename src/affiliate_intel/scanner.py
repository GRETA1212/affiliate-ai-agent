from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import AffiliateProgram


def load_candidates(path: str | Path) -> list[AffiliateProgram]:
    """Load discovered affiliate-program claims from JSON.

    The scanner does not upgrade verification status itself. A separate
    verifier must confirm program terms against authoritative sources.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("candidate file must contain a JSON array")
    return [AffiliateProgram(**item) for item in raw]


def normalize_candidates(candidates: Iterable[AffiliateProgram]) -> list[AffiliateProgram]:
    seen: set[str] = set()
    normalized: list[AffiliateProgram] = []
    for program in candidates:
        program.slug = program.slug.strip().lower().replace(" ", "-")
        program.name = program.name.strip()
        program.validate()
        if program.slug in seen:
            continue
        seen.add(program.slug)
        normalized.append(program)
    return normalized
