from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.connectors.base import BaseConnector, ConnectorContext, ConnectorRecord


class DemoCatalogConnector(BaseConnector):
    def __init__(self, connector_key: str, category: str, display_name: str) -> None:
        self.key = connector_key
        self.category = category
        self.display_name = display_name
        self._catalog_path = Path(__file__).with_name("demo_catalog.json")

    def fetch(self, context: ConnectorContext) -> list[ConnectorRecord]:
        catalog = json.loads(self._catalog_path.read_text())
        records: list[ConnectorRecord] = []
        for item in catalog["items"]:
            if item["connector_key"] != self.key:
                continue
            published_at = item.get("published_at")
            records.append(
                ConnectorRecord(
                    category=item["category"],
                    title=item["title"],
                    source_name=item["source_name"],
                    source_url=item["source_url"],
                    external_identifier=item["external_identifier"],
                    summary=item["summary"],
                    tags=item.get("tags", []),
                    published_at=datetime.fromisoformat(published_at) if published_at else None,
                    location_summary=item.get("location_summary"),
                    raw_payload=item,
                    gaps=item.get("gaps", []),
                    evidence_label=item.get("evidence_label"),
                    evidence_snippet=item.get("evidence_snippet"),
                )
            )
        return records

    def healthcheck(self) -> tuple[bool, str]:
        return True, "Demo source ready"
