import os

from app.connectors.base import ConnectorStatus


def status() -> ConnectorStatus:
    return ConnectorStatus(
        name="youtube",
        configured=bool(os.getenv("YOUTUBE_API_KEY")),
        note="YouTube competition research is planned for V2.",
    )
