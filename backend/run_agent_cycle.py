import json

from app.services.automation_loop import plan_work
from app.services.business_controller import profit_summary


def main() -> None:
    run = plan_work(limit=10)
    output = {
        "plan": run.model_dump(),
        "profit": profit_summary().model_dump(),
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
