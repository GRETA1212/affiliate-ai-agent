import os

from app.connectors.base import ConnectorStatus


def status() -> ConnectorStatus:
    return ConnectorStatus(
        name="impact",
        configured=bool(os.getenv("IMPACT_ACCOUNT_SID") and os.getenv("IMPACT_AUTH_TOKEN")),
        note="Live Impact Partner API calls are planned for V2.",
    )
