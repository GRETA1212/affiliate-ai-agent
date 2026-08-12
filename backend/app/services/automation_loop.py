from pydantic import BaseModel

from app.services.business_controller import ContentJobCreate, enqueue_content_job, next_actions


class AutomationRun(BaseModel):
    planned_actions: int
    queued_jobs: list[str]


def plan_work(limit: int = 10) -> AutomationRun:
    """Translate measured campaign signals into concrete queued work.

    This function deliberately does not auto-publish or spend money. It prepares auditable
    jobs that another worker can execute after program/platform rules and credentials allow it.
    """
    queued: list[str] = []
    actions = next_actions(limit=limit)

    for item in actions:
        if item.action == "prepare-launch":
            job = ContentJobCreate(
                campaign_id=item.campaign_id,
                job_type="launch-checklist",
                title="Prepare campaign for compliant launch",
                priority=item.priority,
                brief={
                    "requirements": [
                        "approved affiliate tracking URL",
                        "visible affiliate disclosure",
                        "fact-checked claims",
                        "public HTTPS tracking route",
                    ],
                    "reason": item.reason,
                },
            )
        elif item.action == "collect-qualified-traffic":
            job = ContentJobCreate(
                campaign_id=item.campaign_id,
                job_type="traffic-plan",
                title="Create qualified organic traffic plan",
                priority=item.priority,
                brief={
                    "channels": ["search", "youtube", "social"],
                    "avoid": ["spam", "fake engagement", "prohibited paid-brand bidding"],
                    "reason": item.reason,
                },
            )
        elif item.action == "run-content-or-cta-experiment":
            job = ContentJobCreate(
                campaign_id=item.campaign_id,
                job_type="experiment-plan",
                title="Design one controlled conversion experiment",
                priority=item.priority,
                brief={
                    "variables": ["headline", "cta-copy", "cta-placement", "comparison-order"],
                    "rule": "change one primary variable at a time",
                    "reason": item.reason,
                },
            )
        elif item.action == "pause-and-rework":
            job = ContentJobCreate(
                campaign_id=item.campaign_id,
                job_type="rework-analysis",
                title="Diagnose non-converting campaign before more traffic",
                priority=item.priority,
                brief={
                    "check": ["search intent", "offer fit", "cta", "page trust", "tracking"],
                    "reason": item.reason,
                },
            )
        else:
            job = ContentJobCreate(
                campaign_id=item.campaign_id,
                job_type="scale-plan",
                title="Expand a campaign with recorded conversions",
                priority=item.priority,
                brief={
                    "actions": [
                        "create adjacent buyer-intent content",
                        "strengthen internal links",
                        "expand proven distribution channel",
                    ],
                    "reason": item.reason,
                },
            )
        queued.append(enqueue_content_job(job))

    return AutomationRun(planned_actions=len(actions), queued_jobs=queued)
