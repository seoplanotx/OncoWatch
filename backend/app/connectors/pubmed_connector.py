from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.connectors.base import BaseConnector, ConnectorContext, ConnectorRecord


class PubMedConnector(BaseConnector):
    key = "pubmed_literature"
    category = "literature"
    display_name = "PubMed literature"

    _search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    _summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    def _build_query(self, context: ConnectorContext) -> str:
        profile = context.profile
        terms: list[str] = []
        if getattr(profile, "cancer_type", None):
            terms.append(f'"{profile.cancer_type}"')
        if getattr(profile, "subtype", None):
            terms.append(f'"{profile.subtype}"')
        for biomarker in getattr(profile, "biomarkers", [])[:3]:
            if biomarker.name:
                marker = biomarker.name if not biomarker.variant else f"{biomarker.name} {biomarker.variant}"
                terms.append(f'"{marker}"')
        if not terms:
            terms.append('"cancer"')
        return " AND ".join(terms)

    def fetch(self, context: ConnectorContext) -> list[ConnectorRecord]:
        query = self._build_query(context)
        retmax = int(context.source_config.settings_json.get("retmax", 5))
        with httpx.Client(timeout=20.0) as client:
            search_response = client.get(
                self._search_url,
                params={
                    "db": "pubmed",
                    "retmode": "json",
                    "sort": "pub+date",
                    "retmax": retmax,
                    "term": query,
                },
            )
            search_response.raise_for_status()
            ids = search_response.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return []

            summary_response = client.get(
                self._summary_url,
                params={
                    "db": "pubmed",
                    "retmode": "json",
                    "id": ",".join(ids),
                },
            )
            summary_response.raise_for_status()
            data = summary_response.json().get("result", {})
            records: list[ConnectorRecord] = []
            for uid in ids:
                item: dict[str, Any] = data.get(uid, {})
                title = item.get("title") or f"PubMed article {uid}"
                journal = item.get("fulljournalname") or item.get("source") or "PubMed"
                pubdate_raw = item.get("pubdate")
                published_at = None
                if pubdate_raw:
                    try:
                        published_at = datetime.fromisoformat(pubdate_raw[:10] + "T00:00:00+00:00")
                    except ValueError:
                        published_at = None

                authors = ", ".join(author.get("name", "") for author in item.get("authors", [])[:3] if author.get("name"))
                snippet = f"{journal}. {authors}".strip().strip(".")
                records.append(
                    ConnectorRecord(
                        category="literature",
                        title=title,
                        source_name="PubMed",
                        source_url=f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                        external_identifier=f"PMID:{uid}",
                        summary=snippet or "Recent PubMed literature item.",
                        tags=[tag for tag in [journal, context.profile.cancer_type, context.profile.subtype] if tag],
                        published_at=published_at,
                        raw_payload=item,
                        gaps=["Abstract text is not included in this MVP literature connector summary."],
                        evidence_label="PubMed summary",
                        evidence_snippet=snippet or title,
                    )
                )
            return records

    def healthcheck(self) -> tuple[bool, str]:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    self._search_url,
                    params={"db": "pubmed", "retmode": "json", "retmax": 1, "term": "cancer"},
                )
                response.raise_for_status()
            return True, "PubMed reachable"
        except Exception as exc:
            return False, f"PubMed check failed: {exc}"
