import json
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.storage import connect

JobStatus = Literal["queued", "running", "done", "failed"]
ExperimentStatus = Literal["draft", "running", "completed", "cancelled"]

BUSINESS_SCHEMA = """
CREATE TABLE IF NOT EXISTS expenses (
    id TEXT PRIMARY KEY,
    campaign_id TEXT REFERENCES campaigns(id) ON DELETE SET NULL,
    category TEXT NOT NULL,
    amount REAL NOT NULL CHECK (amount >= 0),
    currency TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_expenses_campaign_time
    ON expenses(campaign_id, occurred_at);

CREATE TABLE IF NOT EXISTS recommendation_snapshots (
    id TEXT PRIMARY KEY,
    campaign_id TEXT REFERENCES campaigns(id) ON DELETE CASCADE,
    classification TEXT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_recommendations_campaign_time
    ON recommendation_snapshots(campaign_id, created_at);

CREATE TABLE IF NOT EXISTS content_jobs (
    id TEXT PRIMARY KEY,
    campaign_id TEXT REFERENCES campaigns(id) ON DELETE SET NULL,
    job_type TEXT NOT NULL,
    title TEXT NOT NULL,
    brief_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued','running','done','failed')),
    priority INTEGER NOT NULL DEFAULT 50,
    result_json TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_content_jobs_status_priority
    ON content_jobs(status, priority DESC, created_at);

CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    variant_a TEXT NOT NULL,
    variant_b TEXT NOT NULL,
    metric TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('draft','running','completed','cancelled')),
    a_impressions INTEGER NOT NULL DEFAULT 0,
    a_conversions INTEGER NOT NULL DEFAULT 0,
    b_impressions INTEGER NOT NULL DEFAULT 0,
    b_conversions INTEGER NOT NULL DEFAULT 0,
    winner TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class ExpenseCreate(BaseModel):
    amount: float = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    category: str = Field(min_length=2, max_length=80)
    campaign_id: str | None = None
    notes: str | None = Field(default=None, max_length=1000)
    occurred_at: datetime | None = None


class ProfitSummary(BaseModel):
    approved_revenue_by_currency: dict[str, float]
    expenses_by_currency: dict[str, float]
    profit_by_currency: dict[str, float]


class ContentJobCreate(BaseModel):
    job_type: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=200)
    brief: dict = Field(default_factory=dict)
    campaign_id: str | None = None
    priority: int = Field(default=50, ge=0, le=100)


class ExperimentCreate(BaseModel):
    campaign_id: str
    name: str = Field(min_length=2, max_length=160)
    variant_a: str = Field(min_length=1, max_length=500)
    variant_b: str = Field(min_length=1, max_length=500)
    metric: str = Field(default="conversion_rate", min_length=2, max_length=80)


class NextAction(BaseModel):
    campaign_id: str | None = None
    priority: int
    action: str
    reason: str


def ensure_business_schema() -> None:
    connection = connect()
    try:
        connection.executescript(BUSINESS_SCHEMA)
        connection.commit()
    finally:
        connection.close()


def record_expense(data: ExpenseCreate) -> str:
    ensure_business_schema()
    expense_id = uuid4().hex
    now = _now()
    occurred_at = _as_utc(data.occurred_at) if data.occurred_at else now
    connection = connect()
    try:
        if data.campaign_id:
            exists = connection.execute(
                "SELECT 1 FROM campaigns WHERE id = ?", (data.campaign_id,)
            ).fetchone()
            if exists is None:
                raise ValueError("Campaign not found.")
        connection.execute(
            """
            INSERT INTO expenses (
                id, campaign_id, category, amount, currency, occurred_at, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                expense_id,
                data.campaign_id,
                data.category.strip(),
                data.amount,
                data.currency.upper(),
                occurred_at,
                data.notes.strip() if data.notes else None,
                now,
            ),
        )
        connection.commit()
        return expense_id
    finally:
        connection.close()


def profit_summary() -> ProfitSummary:
    ensure_business_schema()
    connection = connect()
    try:
        revenue_rows = connection.execute(
            """
            SELECT currency, SUM(commission_amount) AS amount
            FROM conversions
            WHERE status = 'approved'
            GROUP BY currency
            """
        ).fetchall()
        expense_rows = connection.execute(
            "SELECT currency, SUM(amount) AS amount FROM expenses GROUP BY currency"
        ).fetchall()
    finally:
        connection.close()

    revenue = {
        str(row["currency"]): round(float(row["amount"] or 0), 2)
        for row in revenue_rows
    }
    expenses = {
        str(row["currency"]): round(float(row["amount"] or 0), 2)
        for row in expense_rows
    }
    currencies = set(revenue) | set(expenses)
    profit = {
        code: round(revenue.get(code, 0.0) - expenses.get(code, 0.0), 2)
        for code in currencies
    }
    return ProfitSummary(
        approved_revenue_by_currency=revenue,
        expenses_by_currency=expenses,
        profit_by_currency=profit,
    )


def enqueue_content_job(data: ContentJobCreate) -> str:
    ensure_business_schema()
    job_id = uuid4().hex
    now = _now()
    connection = connect()
    try:
        connection.execute(
            """
            INSERT INTO content_jobs (
                id, campaign_id, job_type, title, brief_json, status, priority,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'queued', ?, ?, ?)
            """,
            (
                job_id,
                data.campaign_id,
                data.job_type.strip(),
                data.title.strip(),
                json.dumps(data.brief, sort_keys=True),
                data.priority,
                now,
                now,
            ),
        )
        connection.commit()
        return job_id
    finally:
        connection.close()


def claim_next_job() -> dict | None:
    ensure_business_schema()
    connection = connect()
    try:
        row = connection.execute(
            """
            SELECT * FROM content_jobs
            WHERE status = 'queued'
            ORDER BY priority DESC, created_at ASC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            return None
        connection.execute(
            "UPDATE content_jobs SET status = 'running', updated_at = ? WHERE id = ?",
            (_now(), row["id"]),
        )
        connection.commit()
        result = dict(row)
        result["status"] = "running"
        result["brief"] = json.loads(result.pop("brief_json"))
        return result
    finally:
        connection.close()


def complete_job(job_id: str, result: dict) -> None:
    ensure_business_schema()
    connection = connect()
    try:
        cursor = connection.execute(
            """
            UPDATE content_jobs
            SET status = 'done', result_json = ?, error = NULL, updated_at = ?
            WHERE id = ?
            """,
            (json.dumps(result, sort_keys=True), _now(), job_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("Job not found.")
        connection.commit()
    finally:
        connection.close()


def fail_job(job_id: str, error: str) -> None:
    ensure_business_schema()
    connection = connect()
    try:
        cursor = connection.execute(
            """
            UPDATE content_jobs
            SET status = 'failed', error = ?, updated_at = ?
            WHERE id = ?
            """,
            (error[:2000], _now(), job_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("Job not found.")
        connection.commit()
    finally:
        connection.close()


def save_recommendation_snapshot(
    campaign_id: str,
    *,
    classification: str,
    action: str,
    reason: str,
    metrics: dict,
) -> str:
    ensure_business_schema()
    snapshot_id = uuid4().hex
    connection = connect()
    try:
        connection.execute(
            """
            INSERT INTO recommendation_snapshots (
                id, campaign_id, classification, action, reason, metrics_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                campaign_id,
                classification,
                action,
                reason,
                json.dumps(metrics, sort_keys=True),
                _now(),
            ),
        )
        connection.commit()
        return snapshot_id
    finally:
        connection.close()


def create_experiment(data: ExperimentCreate) -> str:
    ensure_business_schema()
    experiment_id = uuid4().hex
    now = _now()
    connection = connect()
    try:
        connection.execute(
            """
            INSERT INTO experiments (
                id, campaign_id, name, variant_a, variant_b, metric, status,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'running', ?, ?)
            """,
            (
                experiment_id,
                data.campaign_id,
                data.name.strip(),
                data.variant_a,
                data.variant_b,
                data.metric,
                now,
                now,
            ),
        )
        connection.commit()
        return experiment_id
    finally:
        connection.close()


def record_experiment_observation(
    experiment_id: str,
    variant: Literal["a", "b"],
    converted: bool,
) -> None:
    ensure_business_schema()
    impression_col = f"{variant}_impressions"
    conversion_col = f"{variant}_conversions"
    connection = connect()
    try:
        cursor = connection.execute(
            f"""
            UPDATE experiments
            SET {impression_col} = {impression_col} + 1,
                {conversion_col} = {conversion_col} + ?,
                updated_at = ?
            WHERE id = ? AND status = 'running'
            """,
            (int(converted), _now(), experiment_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("Running experiment not found.")
        connection.commit()
    finally:
        connection.close()


def finish_experiment(
    experiment_id: str,
    minimum_impressions_per_variant: int = 50,
) -> str:
    ensure_business_schema()
    connection = connect()
    try:
        row = connection.execute(
            "SELECT * FROM experiments WHERE id = ?", (experiment_id,)
        ).fetchone()
        if row is None:
            raise ValueError("Experiment not found.")
        if (
            row["a_impressions"] < minimum_impressions_per_variant
            or row["b_impressions"] < minimum_impressions_per_variant
        ):
            raise ValueError("Not enough observations to finish experiment.")
        a_rate = (
            row["a_conversions"] / row["a_impressions"]
            if row["a_impressions"]
            else 0.0
        )
        b_rate = (
            row["b_conversions"] / row["b_impressions"]
            if row["b_impressions"]
            else 0.0
        )
        winner = "a" if a_rate > b_rate else "b" if b_rate > a_rate else "tie"
        connection.execute(
            """
            UPDATE experiments
            SET status = 'completed', winner = ?, updated_at = ?
            WHERE id = ?
            """,
            (winner, _now(), experiment_id),
        )
        connection.commit()
        return winner
    finally:
        connection.close()


def next_actions(limit: int = 10) -> list[NextAction]:
    """Return revenue-focused actions from real campaign data, never fabricated earnings."""
    ensure_business_schema()
    connection = connect()
    try:
        campaigns = connection.execute(
            """
            SELECT c.id, c.name, c.status, c.opportunity_score,
                   SUM(CASE WHEN cl.is_bot = 0 THEN 1 ELSE 0 END) AS human_clicks
            FROM campaigns c
            LEFT JOIN clicks cl ON cl.campaign_id = c.id
            GROUP BY c.id
            ORDER BY COALESCE(c.opportunity_score, 0) DESC, c.updated_at DESC
            """
        ).fetchall()
        conversions = connection.execute(
            """
            SELECT campaign_id, COUNT(*) AS conversions, SUM(commission_amount) AS revenue
            FROM conversions
            WHERE status = 'approved'
            GROUP BY campaign_id
            """
        ).fetchall()
    finally:
        connection.close()

    conversion_map = {
        row["campaign_id"]: (
            int(row["conversions"] or 0),
            float(row["revenue"] or 0),
        )
        for row in conversions
    }
    actions: list[NextAction] = []
    for row in campaigns:
        clicks = int(row["human_clicks"] or 0)
        conversions_count, revenue = conversion_map.get(row["id"], (0, 0.0))
        score = float(row["opportunity_score"] or 0)

        if row["status"] == "draft":
            actions.append(
                NextAction(
                    campaign_id=row["id"],
                    priority=min(100, int(70 + score * 0.3)),
                    action="prepare-launch",
                    reason=(
                        "High-potential draft campaign needs approved tracking link, "
                        "disclosure and publication."
                    ),
                )
            )
        elif clicks < 50:
            actions.append(
                NextAction(
                    campaign_id=row["id"],
                    priority=75,
                    action="collect-qualified-traffic",
                    reason=(
                        f"Only {clicks} human clicks; there is not enough evidence "
                        "to optimize safely."
                    ),
                )
            )
        elif conversions_count == 0 and clicks >= 150:
            actions.append(
                NextAction(
                    campaign_id=row["id"],
                    priority=95,
                    action="pause-and-rework",
                    reason=(
                        f"{clicks} human clicks with no approved conversion; rework "
                        "intent, offer or CTA before scaling."
                    ),
                )
            )
        elif conversions_count == 0:
            actions.append(
                NextAction(
                    campaign_id=row["id"],
                    priority=85,
                    action="run-content-or-cta-experiment",
                    reason=(
                        f"{clicks} human clicks without a conversion; test one "
                        "controlled variable."
                    ),
                )
            )
        elif revenue > 0:
            actions.append(
                NextAction(
                    campaign_id=row["id"],
                    priority=90,
                    action="scale-proven-campaign",
                    reason=(
                        f"Campaign has {conversions_count} approved conversion(s) "
                        "and recorded commission revenue."
                    ),
                )
            )

    actions.sort(key=lambda item: item.priority, reverse=True)
    return actions[:limit]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _as_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()
