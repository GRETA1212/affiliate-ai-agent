from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectorStatus:
    name: str
    configured: bool
    note: str
