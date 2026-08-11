import os

from app.connectors.base import ConnectorStatus


def status() -> ConnectorStatus:
    return ConnectorStatus(
        name="cj",
        configured=bool(os.getenv("CJ_API_TOKEN") and os.getenv("CJ_WEBSITE_ID")),
        note="Live CJ API calls are planned for V2; credentials stay in environment variables.",
    )
