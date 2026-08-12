import os
from datetime import date

from pydantic import BaseModel

from app.connectors import cj, impact
from app.services import network_sync
from app.services.verified_catalog import VERIFIED_PROGRAMS


class StaleProgram(BaseModel):
    advertiser: str
    verified_at: date
    age_days: int


class MaintenanceReport(BaseModel):
    stale_programs: list[StaleProgram]
    network_sync_attempted: list[str]
    network_sync_skipped: list[str]


def stale_verified_programs(max_age_days: int = 14) -> list[StaleProgram]:
    today = date.today()
    stale: list[StaleProgram] = []
    for program in VERIFIED_PROGRAMS:
        age = (today - program.verified_at).days
        if age > max_age_days:
            stale.append(
                StaleProgram(
                    advertiser=program.advertiser,
                    verified_at=program.verified_at,
                    age_days=age,
                )
            )
    return stale


def run_maintenance(max_fact_age_days: int = 14, lookback_days: int = 7) -> MaintenanceReport:
    configured: list[str] = []
    skipped: list[str] = []

    if cj.commission_status().configured:
        configured.append("cj")
    else:
        skipped.append("cj")

    if impact.status().configured:
        configured.append("impact")
    else:
        skipped.append("impact")

    if configured and os.getenv("AFFILIATE_ENABLE_NETWORK_SYNC", "0") == "1":
        network_sync.sync_networks(
            network_sync.SyncRequest(networks=configured, lookback_days=lookback_days)
        )
    elif configured:
        skipped.extend(configured)
        configured = []

    return MaintenanceReport(
        stale_programs=stale_verified_programs(max_age_days=max_fact_age_days),
        network_sync_attempted=configured,
        network_sync_skipped=sorted(set(skipped)),
    )
