import re
import sqlite3
import unicodedata
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl

from app.storage import connect

CampaignStatus = Literal["draft", "active", "paused", "archived"]
ConversionStatus = Literal["pending", "approved", "reversed"]


class WorkspaceError(RuntimeError):
    pass


class WorkspaceNotFound(WorkspaceError):
    pass


class WorkspaceConflict(WorkspaceError):
    pass


class WorkspaceInactive(WorkspaceError):
    pass


class CampaignCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    product_name: str = Field(min_length=1, max_length=160)
    audience: str = Field(default="", max_length=500)
    problem: str = Field(default="", max_length=1000)
    affiliate_url: HttpUrl
    slug: str | None = Field(default=None, min_length=2, max_length=100)
    status: CampaignStatus = "draft"
    source: str | None = Field(default=None, max_length=80)
    opportunity_score: float | None = Field(default=None, ge=0, le=100)


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    audience: str | None = Field(default=None, max_length=500)
    problem: str | None = Field(default=None, max_length=1000)
    affiliate_url: HttpUrl | None = None
    status: CampaignStatus | None = None


class CampaignRecord(BaseModel):
    id: str
    name: str
    product_name: str
    audience: str
    problem: str
    affiliate_url: str
    slug: str
    status: CampaignStatus
    source: str | None
    opportunity_score: float | None
    created_at: str
    updated_at: str


class ConversionCreate(BaseModel):
    commission_amount: float = Field(ge=0)
    sale_amount: float | None = Field(default=None, ge=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    status: ConversionStatus = "approved"
    network: str | None = Field(default=None, max_length=80)
    external_id: str | None = Field(default=None, max_length=200)
    occurred_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=1000)


class ConversionUpdate(BaseModel):
    status: ConversionStatus


class ConversionRecord(BaseModel):
    id: str
    campaign_id: str
    occurred_at: str
    network: str | None
    external_id: str | None
    status: ConversionStatus
    sale_amount: float | None
    commission_amount: float
    currency: str
    notes: str | None
    created_at: str
    updated_at: str


class CampaignMetrics(BaseModel):
    campaign_id: str
    total_clicks: int
    human_clicks: int
    bot_clicks: int
    approved_conversions: int
    pending_conversions: int
    reversed_conversions: int
    conversion_rate: float
    approved_revenue_by_currency: dict[str, float]
    pending_revenue_by_currency: dict[str, float]
    gross_sales_by_currency: dict[str, float]
    epc_by_currency: dict[str, float]
    last_click_at: str | None
    last_conversion_at: str | None


class CampaignDetail(BaseModel):
    campaign: CampaignRecord
    metrics: CampaignMetrics


class WorkspaceSummary(BaseModel):
    total_campaigns: int
    active_campaigns: int
    human_clicks: int
    approved_conversions: int
    conversion_rate: float
    approved_revenue_by_currency: dict[str, float]
    epc_by_currency: dict[str, float]


def create_campaign(data: CampaignCreate) -> CampaignDetail:
    now = _utc_now()
    campaign_id = uuid4().hex
    connection = connect()
    try:
        slug = _resolve_slug(connection, data.slug, data.name)
        connection.execute(
            """
            INSERT INTO campaigns (
                id, name, product_name, audience, problem, affiliate_url, slug, status,
                source, opportunity_score, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                campaign_id,
                data.name.strip(),
                data.product_name.strip(),
                data.audience.strip(),
                data.problem.strip(),
                str(data.affiliate_url),
                slug,
                data.status,
                data.source.strip() if data.source else None,
                data.opportunity_score,
                now,
                now,
            ),
        )
        connection.commit()
        return _campaign_detail(connection, campaign_id)
    finally:
        connection.close()


def list_campaigns(status: CampaignStatus | None = None) -> list[CampaignDetail]:
    connection = connect()
    try:
        if status:
            rows = connection.execute(
                "SELECT * FROM campaigns WHERE status = ? ORDER BY updated_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM campaigns ORDER BY updated_at DESC"
            ).fetchall()
        return [
            CampaignDetail(campaign=_campaign_from_row(row), metrics=_metrics(connection, row["id"]))
            for row in rows
        ]
    finally:
        connection.close()


def get_campaign(campaign_id: str) -> CampaignDetail:
    connection = connect()
    try:
        return _campaign_detail(connection, campaign_id)
    finally:
        connection.close()


def update_campaign(campaign_id: str, data: CampaignUpdate) -> CampaignDetail:
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        return get_campaign(campaign_id)
    if "affiliate_url" in updates and updates["affiliate_url"] is not None:
        updates["affiliate_url"] = str(updates["affiliate_url"])
    updates["updated_at"] = _utc_now()
    allowed = {"name", "audience", "problem", "affiliate_url", "status", "updated_at"}
    assignments = ", ".join(f"{field} = ?" for field in updates if field in allowed)
    values = [updates[field] for field in updates if field in allowed]
    connection = connect()
    try:
        cursor = connection.execute(
            f"UPDATE campaigns SET {assignments} WHERE id = ?",
            (*values, campaign_id),
        )
        if cursor.rowcount == 0:
            raise WorkspaceNotFound("Campaign not found.")
        connection.commit()
        return _campaign_detail(connection, campaign_id)
    finally:
        connection.close()


def record_click(
    slug: str,
    *,
    source: str | None = None,
    medium: str | None = None,
    content: str | None = None,
    referrer: str | None = None,
    user_agent: str | None = None,
) -> str:
    connection = connect()
    try:
        campaign = connection.execute(
            "SELECT id, affiliate_url, status FROM campaigns WHERE slug = ?",
            (slug,),
        ).fetchone()
        if campaign is None:
            raise WorkspaceNotFound("Tracking campaign not found.")
        if campaign["status"] != "active":
            raise WorkspaceInactive("Tracking campaign is not active.")
        connection.execute(
            """
            INSERT INTO clicks (
                campaign_id, occurred_at, source, medium, content, referrer, user_agent, is_bot
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                campaign["id"],
                _utc_now(),
                _clean_short(source),
                _clean_short(medium),
                _clean_short(content),
                _trim(referrer, 1000),
                _trim(user_agent, 1000),
                int(_looks_like_bot(user_agent)),
            ),
        )
        connection.commit()
        return str(campaign["affiliate_url"])
    finally:
        connection.close()


def add_conversion(campaign_id: str, data: ConversionCreate) -> ConversionRecord:
    connection = connect()
    try:
        _require_campaign(connection, campaign_id)
        conversion_id = uuid4().hex
        now = _utc_now()
        occurred_at = _datetime_to_utc(data.occurred_at) if data.occurred_at else now
        try:
            connection.execute(
                """
                INSERT INTO conversions (
                    id, campaign_id, occurred_at, network, external_id, status, sale_amount,
                    commission_amount, currency, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversion_id,
                    campaign_id,
                    occurred_at,
                    data.network.strip() if data.network else None,
                    data.external_id.strip() if data.external_id else None,
                    data.status,
                    data.sale_amount,
                    data.commission_amount,
                    data.currency.upper(),
                    data.notes.strip() if data.notes else None,
                    now,
                    now,
                ),
            )
        except sqlite3.IntegrityError as exc:
            if data.external_id:
                raise WorkspaceConflict(
                    "A conversion with this network/external ID already exists."
                ) from exc
            raise
        connection.commit()
        row = connection.execute(
            "SELECT * FROM conversions WHERE id = ?",
            (conversion_id,),
        ).fetchone()
        if row is None:
            raise WorkspaceNotFound("Conversion was not saved.")
        return _conversion_from_row(row)
    finally:
        connection.close()


def update_conversion(conversion_id: str, data: ConversionUpdate) -> ConversionRecord:
    connection = connect()
    try:
        cursor = connection.execute(
            "UPDATE conversions SET status = ?, updated_at = ? WHERE id = ?",
            (data.status, _utc_now(), conversion_id),
        )
        if cursor.rowcount == 0:
            raise WorkspaceNotFound("Conversion not found.")
        connection.commit()
        row = connection.execute(
            "SELECT * FROM conversions WHERE id = ?",
            (conversion_id,),
        ).fetchone()
        if row is None:
            raise WorkspaceNotFound("Conversion not found.")
        return _conversion_from_row(row)
    finally:
        connection.close()


def list_conversions(campaign_id: str) -> list[ConversionRecord]:
    connection = connect()
    try:
        _require_campaign(connection, campaign_id)
        rows = connection.execute(
            "SELECT * FROM conversions WHERE campaign_id = ? ORDER BY occurred_at DESC",
            (campaign_id,),
        ).fetchall()
        return [_conversion_from_row(row) for row in rows]
    finally:
        connection.close()


def campaign_metrics(campaign_id: str) -> CampaignMetrics:
    connection = connect()
    try:
        _require_campaign(connection, campaign_id)
        return _metrics(connection, campaign_id)
    finally:
        connection.close()


def workspace_summary() -> WorkspaceSummary:
    connection = connect()
    try:
        campaign_row = connection.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active
            FROM campaigns
            """
        ).fetchone()
        click_row = connection.execute(
            "SELECT SUM(CASE WHEN is_bot = 0 THEN 1 ELSE 0 END) AS human FROM clicks"
        ).fetchone()
        conversion_row = connection.execute(
            """
            SELECT COUNT(*) AS approved
            FROM conversions
            WHERE status = 'approved'
            """
        ).fetchone()
        revenue_rows = connection.execute(
            """
            SELECT currency, SUM(commission_amount) AS revenue
            FROM conversions
            WHERE status = 'approved'
            GROUP BY currency
            """
        ).fetchall()
        human_clicks = int((click_row["human"] if click_row else 0) or 0)
        approved = int((conversion_row["approved"] if conversion_row else 0) or 0)
        revenue = {
            str(row["currency"]): round(float(row["revenue"] or 0), 2)
            for row in revenue_rows
        }
        epc = {
            currency: round(amount / human_clicks, 4) if human_clicks else 0.0
            for currency, amount in revenue.items()
        }
        return WorkspaceSummary(
            total_campaigns=int((campaign_row["total"] if campaign_row else 0) or 0),
            active_campaigns=int((campaign_row["active"] if campaign_row else 0) or 0),
            human_clicks=human_clicks,
            approved_conversions=approved,
            conversion_rate=round(approved / human_clicks, 4) if human_clicks else 0.0,
            approved_revenue_by_currency=revenue,
            epc_by_currency=epc,
        )
    finally:
        connection.close()


def _campaign_detail(connection: sqlite3.Connection, campaign_id: str) -> CampaignDetail:
    row = _require_campaign(connection, campaign_id)
    return CampaignDetail(campaign=_campaign_from_row(row), metrics=_metrics(connection, campaign_id))


def _require_campaign(connection: sqlite3.Connection, campaign_id: str) -> sqlite3.Row:
    row = connection.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    if row is None:
        raise WorkspaceNotFound("Campaign not found.")
    return row


def _metrics(connection: sqlite3.Connection, campaign_id: str) -> CampaignMetrics:
    click_row = connection.execute(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN is_bot = 0 THEN 1 ELSE 0 END) AS human,
               SUM(CASE WHEN is_bot = 1 THEN 1 ELSE 0 END) AS bots,
               MAX(occurred_at) AS last_click
        FROM clicks
        WHERE campaign_id = ?
        """,
        (campaign_id,),
    ).fetchone()
    conversion_row = connection.execute(
        """
        SELECT SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) AS approved,
               SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending,
               SUM(CASE WHEN status = 'reversed' THEN 1 ELSE 0 END) AS reversed,
               MAX(occurred_at) AS last_conversion
        FROM conversions
        WHERE campaign_id = ?
        """,
        (campaign_id,),
    ).fetchone()
    revenue_rows = connection.execute(
        """
        SELECT currency,
               SUM(CASE WHEN status = 'approved' THEN commission_amount ELSE 0 END) AS approved_revenue,
               SUM(CASE WHEN status = 'pending' THEN commission_amount ELSE 0 END) AS pending_revenue,
               SUM(CASE WHEN status = 'approved' THEN COALESCE(sale_amount, 0) ELSE 0 END) AS gross_sales
        FROM conversions
        WHERE campaign_id = ?
        GROUP BY currency
        """,
        (campaign_id,),
    ).fetchall()
    total = int((click_row["total"] if click_row else 0) or 0)
    human = int((click_row["human"] if click_row else 0) or 0)
    bots = int((click_row["bots"] if click_row else 0) or 0)
    approved = int((conversion_row["approved"] if conversion_row else 0) or 0)
    approved_revenue = {
        str(row["currency"]): round(float(row["approved_revenue"] or 0), 2)
        for row in revenue_rows
        if float(row["approved_revenue"] or 0) != 0
    }
    pending_revenue = {
        str(row["currency"]): round(float(row["pending_revenue"] or 0), 2)
        for row in revenue_rows
        if float(row["pending_revenue"] or 0) != 0
    }
    gross_sales = {
        str(row["currency"]): round(float(row["gross_sales"] or 0), 2)
        for row in revenue_rows
        if float(row["gross_sales"] or 0) != 0
    }
    return CampaignMetrics(
        campaign_id=campaign_id,
        total_clicks=total,
        human_clicks=human,
        bot_clicks=bots,
        approved_conversions=approved,
        pending_conversions=int((conversion_row["pending"] if conversion_row else 0) or 0),
        reversed_conversions=int((conversion_row["reversed"] if conversion_row else 0) or 0),
        conversion_rate=round(approved / human, 4) if human else 0.0,
        approved_revenue_by_currency=approved_revenue,
        pending_revenue_by_currency=pending_revenue,
        gross_sales_by_currency=gross_sales,
        epc_by_currency={
            currency: round(amount / human, 4) if human else 0.0
            for currency, amount in approved_revenue.items()
        },
        last_click_at=str(click_row["last_click"]) if click_row and click_row["last_click"] else None,
        last_conversion_at=(
            str(conversion_row["last_conversion"])
            if conversion_row and conversion_row["last_conversion"]
            else None
        ),
    )


def _campaign_from_row(row: sqlite3.Row) -> CampaignRecord:
    return CampaignRecord(
        id=str(row["id"]),
        name=str(row["name"]),
        product_name=str(row["product_name"]),
        audience=str(row["audience"]),
        problem=str(row["problem"]),
        affiliate_url=str(row["affiliate_url"]),
        slug=str(row["slug"]),
        status=row["status"],
        source=str(row["source"]) if row["source"] else None,
        opportunity_score=(
            float(row["opportunity_score"]) if row["opportunity_score"] is not None else None
        ),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _conversion_from_row(row: sqlite3.Row) -> ConversionRecord:
    return ConversionRecord(
        id=str(row["id"]),
        campaign_id=str(row["campaign_id"]),
        occurred_at=str(row["occurred_at"]),
        network=str(row["network"]) if row["network"] else None,
        external_id=str(row["external_id"]) if row["external_id"] else None,
        status=row["status"],
        sale_amount=float(row["sale_amount"]) if row["sale_amount"] is not None else None,
        commission_amount=float(row["commission_amount"]),
        currency=str(row["currency"]),
        notes=str(row["notes"]) if row["notes"] else None,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _resolve_slug(connection: sqlite3.Connection, requested: str | None, name: str) -> str:
    if requested:
        slug = _slugify(requested)
        exists = connection.execute("SELECT 1 FROM campaigns WHERE slug = ?", (slug,)).fetchone()
        if exists:
            raise WorkspaceConflict("Campaign slug already exists.")
        return slug
    base = _slugify(name)
    slug = base
    while connection.execute("SELECT 1 FROM campaigns WHERE slug = ?", (slug,)).fetchone():
        slug = f"{base}-{uuid4().hex[:6]}"
    return slug


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug[:90] or f"campaign-{uuid4().hex[:6]}"


def _looks_like_bot(user_agent: str | None) -> bool:
    return bool(
        user_agent
        and re.search(
            r"\b(bot|crawler|spider|slurp|headless|preview)\b",
            user_agent,
            re.IGNORECASE,
        )
    )


def _clean_short(value: str | None) -> str | None:
    return _trim(value, 200)


def _trim(value: str | None, max_length: int) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    return cleaned[:max_length] or None


def _datetime_to_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
