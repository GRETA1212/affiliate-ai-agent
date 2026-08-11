import json
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl

from app.connectors import cj, impact
from app.storage import connect

NetworkName = Literal["cj", "impact"]


class SyncError(RuntimeError):
    pass


class SyncNotFound(SyncError):
    pass


class SyncConflict(SyncError):
    pass


class CampaignBindingRequest(BaseModel):
    network: NetworkName
    program_id: str | None = Field(default=None, max_length=100)
    attribution_token: str | None = Field(default=None, min_length=1, max_length=100)


class CampaignBinding(BaseModel):
    campaign_id: str
    network: NetworkName
    program_id: str | None
    attribution_token: str
    created_at: str
    updated_at: str


class ImpactTrackingLinkRequest(BaseModel):
    program_id: str = Field(min_length=1, max_length=100)
    deep_link: HttpUrl | None = None
    media_property_id: str | None = Field(default=None, max_length=100)


class ImpactTrackingLinkResult(BaseModel):
    tracking_url: str
    binding: CampaignBinding


class SyncRequest(BaseModel):
    networks: list[NetworkName] = Field(default_factory=lambda: ["cj", "impact"])
    lookback_days: int = Field(default=7, ge=1, le=31)


class NetworkSyncResult(BaseModel):
    network: NetworkName
    fetched: int
    imported_or_updated: int
    matched: int
    unmatched: int
    conversions_upserted: int
    warning: str | None = None


class SyncResponse(BaseModel):
    started_at: str
    finished_at: str
    results: list[NetworkSyncResult]


class NetworkEventRecord(BaseModel):
    id: str
    network: NetworkName
    external_id: str
    group_id: str
    program_id: str | None
    advertiser_name: str | None
    network_status: str | None
    status: str
    sale_amount: float | None
    commission_amount: float
    currency: str
    occurred_at: str
    order_id: str | None
    attribution_token: str | None
    campaign_id: str | None
    synced_at: str


class SyncStateRecord(BaseModel):
    network: NetworkName
    last_success_at: str | None
    last_cursor: str | None
    last_error: str | None
    updated_at: str


def bind_campaign(campaign_id: str, data: CampaignBindingRequest) -> CampaignBinding:
    connection = connect()
    try:
        campaign = _require_campaign(connection, campaign_id)
        token = data.attribution_token or str(campaign["slug"])
        now = _utc_now()
        try:
            connection.execute(
                """
                INSERT INTO campaign_bindings (
                    campaign_id, network, program_id, attribution_token, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(campaign_id) DO UPDATE SET
                    network = excluded.network,
                    program_id = excluded.program_id,
                    attribution_token = excluded.attribution_token,
                    updated_at = excluded.updated_at
                """,
                (campaign_id, data.network, data.program_id, token, now, now),
            )
        except sqlite3.IntegrityError as exc:
            raise SyncConflict(
                "That network attribution token is already bound to another campaign."
            ) from exc
        connection.commit()
        row = connection.execute(
            "SELECT * FROM campaign_bindings WHERE campaign_id = ?",
            (campaign_id,),
        ).fetchone()
        if row is None:
            raise SyncNotFound("Campaign binding was not saved.")
        return _binding_from_row(row)
    finally:
        connection.close()


def get_binding(campaign_id: str) -> CampaignBinding:
    connection = connect()
    try:
        _require_campaign(connection, campaign_id)
        row = connection.execute(
            "SELECT * FROM campaign_bindings WHERE campaign_id = ?",
            (campaign_id,),
        ).fetchone()
        if row is None:
            raise SyncNotFound("Campaign has no network binding.")
        return _binding_from_row(row)
    finally:
        connection.close()


def create_tagged_impact_link(
    campaign_id: str,
    data: ImpactTrackingLinkRequest,
) -> ImpactTrackingLinkResult:
    connection = connect()
    try:
        campaign = _require_campaign(connection, campaign_id)
        slug = str(campaign["slug"])
    finally:
        connection.close()

    generated = impact.create_tracking_link(
        data.program_id,
        sub_id1=slug,
        deep_link=str(data.deep_link) if data.deep_link else None,
        media_property_id=data.media_property_id,
    )

    connection = connect()
    try:
        now = _utc_now()
        connection.execute(
            "UPDATE campaigns SET affiliate_url = ?, updated_at = ? WHERE id = ?",
            (generated.tracking_url, now, campaign_id),
        )
        connection.commit()
    finally:
        connection.close()

    binding = bind_campaign(
        campaign_id,
        CampaignBindingRequest(
            network="impact",
            program_id=data.program_id,
            attribution_token=slug,
        ),
    )
    return ImpactTrackingLinkResult(
        tracking_url=generated.tracking_url,
        binding=binding,
    )


def sync_networks(request: SyncRequest) -> SyncResponse:
    started = _utc_now()
    now = datetime.now(UTC)
    since = now - timedelta(days=request.lookback_days)
    results: list[NetworkSyncResult] = []
    seen: set[NetworkName] = set()

    for network in request.networks:
        if network in seen:
            continue
        seen.add(network)
        try:
            if network == "impact":
                result = _sync_impact(since, now)
            else:
                result = _sync_cj(since, now)
            _save_sync_state(network, success=True, cursor=None, error=None)
        except (
            cj.CJConfigurationError,
            cj.CJAPIError,
            impact.ImpactConfigurationError,
            impact.ImpactAPIError,
        ) as exc:
            message = str(exc)
            _save_sync_state(network, success=False, cursor=None, error=message)
            result = NetworkSyncResult(
                network=network,
                fetched=0,
                imported_or_updated=0,
                matched=0,
                unmatched=0,
                conversions_upserted=0,
                warning=message,
            )
        results.append(result)

    return SyncResponse(
        started_at=started,
        finished_at=_utc_now(),
        results=results,
    )


def list_unmatched_events(limit: int = 100) -> list[NetworkEventRecord]:
    connection = connect()
    try:
        rows = connection.execute(
            """
            SELECT *
            FROM network_events
            WHERE campaign_id IS NULL
            ORDER BY occurred_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [_event_from_row(row) for row in rows]
    finally:
        connection.close()


def assign_event(event_id: str, campaign_id: str) -> NetworkEventRecord:
    connection = connect()
    try:
        _require_campaign(connection, campaign_id)
        event = connection.execute(
            "SELECT * FROM network_events WHERE id = ?",
            (event_id,),
        ).fetchone()
        if event is None:
            raise SyncNotFound("Network event not found.")

        if event["network"] == "cj":
            connection.execute(
                """
                UPDATE network_events
                SET campaign_id = ?
                WHERE network = 'cj' AND group_id = ?
                """,
                (campaign_id, event["group_id"]),
            )
        else:
            connection.execute(
                "UPDATE network_events SET campaign_id = ? WHERE id = ?",
                (campaign_id, event_id),
            )
        connection.commit()

        if event["network"] == "cj":
            _reconcile_cj_group(connection, str(event["group_id"]))
        else:
            updated = connection.execute(
                "SELECT * FROM network_events WHERE id = ?",
                (event_id,),
            ).fetchone()
            if updated is None:
                raise SyncNotFound("Network event not found after assignment.")
            _materialize_impact_conversion(connection, updated)
        connection.commit()

        row = connection.execute(
            "SELECT * FROM network_events WHERE id = ?",
            (event_id,),
        ).fetchone()
        if row is None:
            raise SyncNotFound("Network event not found after assignment.")
        return _event_from_row(row)
    finally:
        connection.close()


def list_sync_state() -> list[SyncStateRecord]:
    connection = connect()
    try:
        rows = connection.execute("SELECT * FROM sync_state ORDER BY network").fetchall()
        return [_sync_state_from_row(row) for row in rows]
    finally:
        connection.close()


def _sync_impact(start_date: datetime, end_date: datetime) -> NetworkSyncResult:
    page = 1
    fetched = 0
    imported = 0
    matched = 0
    unmatched = 0
    conversions = 0
    warning: str | None = None

    while True:
        response = impact.list_actions(start_date, end_date, page=page)
        fetched += len(response.actions)
        connection = connect()
        try:
            for action in response.actions:
                campaign_id = _match_campaign(
                    connection,
                    "impact",
                    action.campaign_id,
                    action.sub_id1,
                )
                event = _impact_event(action, campaign_id)
                stored = _upsert_event(connection, event)
                imported += 1
                if stored["campaign_id"]:
                    matched += 1
                    _materialize_impact_conversion(connection, stored)
                    conversions += 1
                else:
                    unmatched += 1
            connection.commit()
        finally:
            connection.close()

        if response.num_pages is None or page >= response.num_pages:
            break
        if page >= 10:
            warning = "Impact sync stopped at 10 pages; narrow the lookback window."
            break
        page += 1

    return NetworkSyncResult(
        network="impact",
        fetched=fetched,
        imported_or_updated=imported,
        matched=matched,
        unmatched=unmatched,
        conversions_upserted=conversions,
        warning=warning,
    )


def _sync_cj(start_date: datetime, end_date: datetime) -> NetworkSyncResult:
    cursor: str | None = None
    fetched = 0
    imported = 0
    matched = 0
    unmatched = 0
    affected_groups: set[str] = set()
    warning: str | None = None

    for page_number in range(1, 21):
        previous_cursor = cursor
        response = cj.list_commissions(
            start_date,
            end_date,
            since_commission_id=cursor,
        )
        fetched += len(response.records)
        connection = connect()
        try:
            for record in response.records:
                group_id = record.original_action_id or record.order_id or record.commission_id
                campaign_id = _match_campaign(
                    connection,
                    "cj",
                    record.advertiser_id,
                    record.shopper_id,
                )
                event = _cj_event(record, group_id, campaign_id)
                stored = _upsert_event(connection, event)
                affected_groups.add(group_id)
                imported += 1
                if stored["campaign_id"]:
                    matched += 1
                else:
                    unmatched += 1
            connection.commit()
        finally:
            connection.close()

        cursor = response.max_commission_id or cursor
        if response.payload_complete:
            break
        if cursor == previous_cursor:
            warning = "CJ sync stopped because the pagination cursor did not advance."
            break
        if page_number == 20:
            warning = "CJ sync stopped after 20 pages; run again with a shorter lookback."

    conversions = 0
    connection = connect()
    try:
        for group_id in affected_groups:
            if _reconcile_cj_group(connection, group_id):
                conversions += 1
        connection.commit()
    finally:
        connection.close()

    _save_sync_state("cj", success=True, cursor=cursor, error=None)
    return NetworkSyncResult(
        network="cj",
        fetched=fetched,
        imported_or_updated=imported,
        matched=matched,
        unmatched=unmatched,
        conversions_upserted=conversions,
        warning=warning,
    )


def _impact_event(action: impact.ImpactAction, campaign_id: str | None) -> dict[str, object]:
    status = _impact_status(action.state)
    occurred_at = action.event_date or action.creation_date or _utc_now()
    return {
        "network": "impact",
        "external_id": action.id,
        "group_id": action.id,
        "program_id": action.campaign_id,
        "advertiser_name": action.campaign_name,
        "network_status": action.state,
        "status": status,
        "sale_amount": action.amount,
        "commission_amount": action.payout,
        "currency": action.currency.upper(),
        "occurred_at": occurred_at,
        "order_id": action.oid,
        "attribution_token": action.sub_id1,
        "campaign_id": campaign_id,
        "payload_json": json.dumps(action.model_dump(mode="json"), sort_keys=True),
    }


def _cj_event(
    record: cj.CJCommissionRecord,
    group_id: str,
    campaign_id: str | None,
) -> dict[str, object]:
    return {
        "network": "cj",
        "external_id": record.commission_id,
        "group_id": group_id,
        "program_id": record.advertiser_id,
        "advertiser_name": record.advertiser_name,
        "network_status": record.action_status,
        "status": _cj_status(record.action_status),
        "sale_amount": record.sale_amount_usd,
        "commission_amount": record.commission_amount_usd,
        "currency": "USD",
        "occurred_at": record.event_date or record.posting_date or _utc_now(),
        "order_id": record.order_id,
        "attribution_token": record.shopper_id,
        "campaign_id": campaign_id,
        "payload_json": json.dumps(record.model_dump(mode="json"), sort_keys=True),
    }


def _upsert_event(
    connection: sqlite3.Connection,
    event: dict[str, object],
) -> sqlite3.Row:
    now = _utc_now()
    event_id = uuid4().hex
    connection.execute(
        """
        INSERT INTO network_events (
            id, network, external_id, group_id, program_id, advertiser_name,
            network_status, status, sale_amount, commission_amount, currency,
            occurred_at, order_id, attribution_token, campaign_id, payload_json, synced_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(network, external_id) DO UPDATE SET
            group_id = excluded.group_id,
            program_id = excluded.program_id,
            advertiser_name = excluded.advertiser_name,
            network_status = excluded.network_status,
            status = excluded.status,
            sale_amount = excluded.sale_amount,
            commission_amount = excluded.commission_amount,
            currency = excluded.currency,
            occurred_at = excluded.occurred_at,
            order_id = excluded.order_id,
            attribution_token = excluded.attribution_token,
            campaign_id = COALESCE(excluded.campaign_id, network_events.campaign_id),
            payload_json = excluded.payload_json,
            synced_at = excluded.synced_at
        """,
        (
            event_id,
            event["network"],
            event["external_id"],
            event["group_id"],
            event["program_id"],
            event["advertiser_name"],
            event["network_status"],
            event["status"],
            event["sale_amount"],
            event["commission_amount"],
            event["currency"],
            event["occurred_at"],
            event["order_id"],
            event["attribution_token"],
            event["campaign_id"],
            event["payload_json"],
            now,
        ),
    )
    row = connection.execute(
        "SELECT * FROM network_events WHERE network = ? AND external_id = ?",
        (event["network"], event["external_id"]),
    ).fetchone()
    if row is None:
        raise SyncNotFound("Network event was not saved.")
    return row


def _materialize_impact_conversion(
    connection: sqlite3.Connection,
    event: sqlite3.Row,
) -> None:
    campaign_id = event["campaign_id"]
    if not campaign_id:
        return
    _upsert_conversion(
        connection,
        campaign_id=str(campaign_id),
        network="impact",
        external_id=str(event["external_id"]),
        occurred_at=str(event["occurred_at"]),
        status=str(event["status"]),
        sale_amount=_optional_float(event["sale_amount"]),
        commission_amount=max(float(event["commission_amount"] or 0), 0.0),
        currency=str(event["currency"]),
        notes="Auto-synced from Impact action data.",
    )


def _reconcile_cj_group(connection: sqlite3.Connection, group_id: str) -> bool:
    rows = connection.execute(
        """
        SELECT *
        FROM network_events
        WHERE network = 'cj' AND group_id = ?
        ORDER BY occurred_at ASC
        """,
        (group_id,),
    ).fetchall()
    if not rows:
        return False

    campaign_ids = {str(row["campaign_id"]) for row in rows if row["campaign_id"]}
    if len(campaign_ids) != 1:
        return False
    campaign_id = next(iter(campaign_ids))

    net_commission = round(sum(float(row["commission_amount"] or 0) for row in rows), 6)
    net_sale = round(sum(float(row["sale_amount"] or 0) for row in rows), 6)
    has_negative = any(float(row["commission_amount"] or 0) < 0 for row in rows)
    has_pending = any(str(row["status"]) == "pending" for row in rows)

    if net_commission <= 0 and has_negative:
        status = "reversed"
    elif has_pending:
        status = "pending"
    else:
        status = "approved"

    _upsert_conversion(
        connection,
        campaign_id=campaign_id,
        network="cj",
        external_id=f"group:{group_id}",
        occurred_at=str(rows[0]["occurred_at"]),
        status=status,
        sale_amount=max(net_sale, 0.0),
        commission_amount=max(net_commission, 0.0),
        currency="USD",
        notes="Auto-synced from CJ commission-detail deltas.",
    )
    return True


def _upsert_conversion(
    connection: sqlite3.Connection,
    *,
    campaign_id: str,
    network: NetworkName,
    external_id: str,
    occurred_at: str,
    status: str,
    sale_amount: float | None,
    commission_amount: float,
    currency: str,
    notes: str,
) -> None:
    now = _utc_now()
    conversion_id = uuid4().hex
    connection.execute(
        """
        INSERT INTO conversions (
            id, campaign_id, occurred_at, network, external_id, status,
            sale_amount, commission_amount, currency, notes, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(network, external_id) DO UPDATE SET
            campaign_id = excluded.campaign_id,
            occurred_at = excluded.occurred_at,
            status = excluded.status,
            sale_amount = excluded.sale_amount,
            commission_amount = excluded.commission_amount,
            currency = excluded.currency,
            notes = excluded.notes,
            updated_at = excluded.updated_at
        """,
        (
            conversion_id,
            campaign_id,
            occurred_at,
            network,
            external_id,
            status,
            sale_amount,
            commission_amount,
            currency.upper(),
            notes,
            now,
            now,
        ),
    )


def _match_campaign(
    connection: sqlite3.Connection,
    network: NetworkName,
    program_id: str | None,
    token: str | None,
) -> str | None:
    if token:
        row = connection.execute(
            """
            SELECT campaign_id
            FROM campaign_bindings
            WHERE network = ? AND attribution_token = ?
            """,
            (network, token),
        ).fetchone()
        if row is not None:
            return str(row["campaign_id"])

    if not program_id:
        return None
    rows = connection.execute(
        """
        SELECT campaign_id
        FROM campaign_bindings
        WHERE network = ? AND program_id = ?
        """,
        (network, program_id),
    ).fetchall()
    if len(rows) == 1:
        return str(rows[0]["campaign_id"])
    return None


def _require_campaign(connection: sqlite3.Connection, campaign_id: str) -> sqlite3.Row:
    row = connection.execute(
        "SELECT * FROM campaigns WHERE id = ?",
        (campaign_id,),
    ).fetchone()
    if row is None:
        raise SyncNotFound("Campaign not found.")
    return row


def _binding_from_row(row: sqlite3.Row) -> CampaignBinding:
    return CampaignBinding(
        campaign_id=str(row["campaign_id"]),
        network=str(row["network"]),
        program_id=_optional_string(row["program_id"]),
        attribution_token=str(row["attribution_token"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _event_from_row(row: sqlite3.Row) -> NetworkEventRecord:
    return NetworkEventRecord(
        id=str(row["id"]),
        network=str(row["network"]),
        external_id=str(row["external_id"]),
        group_id=str(row["group_id"]),
        program_id=_optional_string(row["program_id"]),
        advertiser_name=_optional_string(row["advertiser_name"]),
        network_status=_optional_string(row["network_status"]),
        status=str(row["status"]),
        sale_amount=_optional_float(row["sale_amount"]),
        commission_amount=float(row["commission_amount"] or 0),
        currency=str(row["currency"]),
        occurred_at=str(row["occurred_at"]),
        order_id=_optional_string(row["order_id"]),
        attribution_token=_optional_string(row["attribution_token"]),
        campaign_id=_optional_string(row["campaign_id"]),
        synced_at=str(row["synced_at"]),
    )


def _sync_state_from_row(row: sqlite3.Row) -> SyncStateRecord:
    return SyncStateRecord(
        network=str(row["network"]),
        last_success_at=_optional_string(row["last_success_at"]),
        last_cursor=_optional_string(row["last_cursor"]),
        last_error=_optional_string(row["last_error"]),
        updated_at=str(row["updated_at"]),
    )


def _save_sync_state(
    network: NetworkName,
    *,
    success: bool,
    cursor: str | None,
    error: str | None,
) -> None:
    connection = connect()
    try:
        now = _utc_now()
        connection.execute(
            """
            INSERT INTO sync_state (
                network, last_success_at, last_cursor, last_error, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(network) DO UPDATE SET
                last_success_at = CASE
                    WHEN excluded.last_success_at IS NOT NULL
                    THEN excluded.last_success_at
                    ELSE sync_state.last_success_at
                END,
                last_cursor = COALESCE(excluded.last_cursor, sync_state.last_cursor),
                last_error = excluded.last_error,
                updated_at = excluded.updated_at
            """,
            (network, now if success else None, cursor, error, now),
        )
        connection.commit()
    finally:
        connection.close()


def _impact_status(value: str | None) -> str:
    normalized = (value or "").strip().upper()
    if normalized == "APPROVED":
        return "approved"
    if normalized == "REVERSED":
        return "reversed"
    return "pending"


def _cj_status(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    return "approved" if normalized in {"locked", "closed"} else "pending"


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value: object) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
