import os

from app.connectors.base import ConnectorStatus


def status() -> ConnectorStatus:
    return ConnectorStatus(
        name="google_ads",
        configured=bool(os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")),
        note="Keyword demand and competition ingestion is planned for V2.",
    )
