from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ConnectorContext:
    profile: Any
    source_config: Any
    requested_at: datetime


@dataclass(slots=True)
class ConnectorRecord:
    category: str
    title: str
    source_name: str
    source_url: str
    external_identifier: str
    summary: str
    tags: list[str] = field(default_factory=list)
    published_at: datetime | None = None
    location_summary: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)
    gaps: list[str] = field(default_factory=list)
    evidence_label: str | None = None
    evidence_snippet: str | None = None


class BaseConnector(ABC):
    key: str
    category: str
    display_name: str

    @abstractmethod
    def fetch(self, context: ConnectorContext) -> list[ConnectorRecord]:
        raise NotImplementedError

    def healthcheck(self) -> tuple[bool, str]:
        return True, "Ready"
