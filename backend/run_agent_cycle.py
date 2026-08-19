import argparse
import json

from app.services.automation_loop import plan_work
from app.services.business_controller import profit_summary
from app.services.job_worker import DEFAULT_MODEL, drain_jobs
from app.services.maintenance import run_maintenance


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one Affiliate AI orchestration cycle.")
    parser.add_argument("--plan-limit", type=int, default=10)
    parser.add_argument("--work-limit", type=int, default=10)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--no-ollama",
        action="store_true",
        help="Use deterministic fallback workers instead of local Ollama.",
    )
    args = parser.parse_args()

    maintenance = run_maintenance()
    run = plan_work(limit=args.plan_limit)
    executed = drain_jobs(
        limit=args.work_limit,
        model=args.model,
        use_ollama=not args.no_ollama,
    )
    output = {
        "maintenance": maintenance.model_dump(mode="json"),
        "plan": run.model_dump(),
        "executed_jobs": executed,
        "profit": profit_summary().model_dump(),
        "safety": {
            "auto_publish": False,
            "auto_spend": False,
            "human_approval_required": True,
        },
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
