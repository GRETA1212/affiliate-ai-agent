from __future__ import annotations

from pydantic import BaseModel

from app.services import business_controller as business
from app.services.movie_content_engine import MovieJobRequest, queue_movie_job
from app.storage import connect


class MovieAutomationRun(BaseModel):
    considered_actions: int
    queued_movies: list[str]
    skipped_campaigns: list[str]


def plan_movie_work(limit: int = 10) -> MovieAutomationRun:
    """Queue affiliate mini-movie work from the existing revenue-focused action engine.

    The movie layer does not invent opportunities or bypass campaign controls. It consumes the
    same measured `next_actions()` used by Affiliate AI and only creates work for campaigns that
    either need qualified traffic or already have approved revenue worth scaling.
    """
    actions = business.next_actions(limit=limit)
    queued: list[str] = []
    skipped: list[str] = []

    for action in actions:
        campaign_id = action.campaign_id
        if not campaign_id:
            continue
        if action.action not in {"collect-qualified-traffic", "scale-proven-campaign"}:
            continue
        if _has_open_movie_job(campaign_id):
            skipped.append(campaign_id)
            continue

        tone = "cinematic" if action.action == "collect-qualified-traffic" else "luxury"
        request = MovieJobRequest(
            campaign_id=campaign_id,
            tone=tone,
            priority=action.priority,
            duration_seconds=70,
            scene_count=9,
        )
        queued.append(queue_movie_job(request).job_id)

    return MovieAutomationRun(
        considered_actions=len(actions),
        queued_movies=queued,
        skipped_campaigns=skipped,
    )


def _has_open_movie_job(campaign_id: str) -> bool:
    business.ensure_business_schema()
    connection = connect()
    try:
        row = connection.execute(
            """
            SELECT 1
            FROM content_jobs
            WHERE campaign_id = ?
              AND job_type = 'affiliate_movie'
              AND status IN ('queued', 'running')
            LIMIT 1
            """,
            (campaign_id,),
        ).fetchone()
        return row is not None
    finally:
        connection.close()
