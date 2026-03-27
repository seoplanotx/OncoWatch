from __future__ import annotations

import calendar
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree as ET

import httpx

from app.connectors.base import BaseConnector, ConnectorContext, ConnectorRecord


class PubMedConnector(BaseConnector):
    key = "pubmed_literature"
    category = "literature"
    display_name = "PubMed literature"

    _search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    _summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    _fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def _build_client(self, timeout: float) -> httpx.Client:
        return httpx.Client(
            timeout=timeout,
            headers={"user-agent": "OncoWatch/0.1"},
        )

    def _build_query(self, context: ConnectorContext) -> str:
        profile = context.profile
        terms: list[str] = []
        if getattr(profile, "cancer_type", None):
            terms.append(f'("{profile.cancer_type}"[Title/Abstract])')
        if getattr(profile, "subtype", None):
            terms.append(f'("{profile.subtype}"[Title/Abstract])')
        for biomarker in getattr(profile, "biomarkers", [])[:3]:
            if biomarker.name:
                marker = biomarker.name if not biomarker.variant else f"{biomarker.name} {biomarker.variant}"
                terms.append(f'("{marker}"[Title/Abstract])')
        if not terms:
            terms.append('"cancer"[Title/Abstract]')
        return " AND ".join(terms)

    def fetch(self, context: ConnectorContext) -> list[ConnectorRecord]:
        query = self._build_query(context)
        retmax = int(context.source_config.settings_json.get("retmax", context.source_config.settings_json.get("page_size", 5)))
        retmax = max(1, min(retmax, 20))
        with self._build_client(20.0) as client:
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

            fetch_response = client.get(
                self._fetch_url,
                params={
                    "db": "pubmed",
                    "retmode": "xml",
                    "id": ",".join(ids),
                },
            )
            fetch_response.raise_for_status()
            abstract_data = self._parse_pubmed_fetch(fetch_response.text)

            records: list[ConnectorRecord] = []
            for uid in ids:
                item: dict[str, Any] = data.get(uid, {})
                title = item.get("title") or f"PubMed article {uid}"
                journal = item.get("fulljournalname") or item.get("source") or "PubMed"
                pubdate_raw = item.get("pubdate")
                published_at = self._parse_pubmed_date(pubdate_raw)

                authors = ", ".join(author.get("name", "") for author in item.get("authors", [])[:3] if author.get("name"))
                article_details = abstract_data.get(uid, {})
                abstract_sections = article_details.get("abstract_sections", [])
                abstract_snippet = self._select_abstract_snippet(
                    abstract_sections,
                    search_terms=[context.profile.cancer_type, context.profile.subtype, *[
                        " ".join(part for part in [biomarker.name, biomarker.variant] if part)
                        for biomarker in getattr(context.profile, "biomarkers", [])
                    ]],
                )
                citation_snippet = ". ".join(part for part in [journal, authors] if part).strip().strip(".")
                summary = abstract_snippet or citation_snippet or "Recent PubMed literature item."
                gaps: list[str] = []
                if not abstract_snippet:
                    gaps.append("PubMed did not provide an abstract for this citation, so only citation metadata is shown.")

                identifiers = {
                    "pmid": uid,
                    **article_details.get("identifiers", {}),
                }

                records.append(
                    ConnectorRecord(
                        category="literature",
                        title=title,
                        source_name="PubMed",
                        source_url=f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                        external_identifier=f"PMID:{uid}",
                        summary=summary,
                        tags=[
                            tag
                            for tag in [journal, context.profile.cancer_type, context.profile.subtype, *article_details.get("mesh_terms", [])[:2]]
                            if tag
                        ],
                        published_at=published_at,
                        raw_payload={
                            "journal": journal,
                            "authors": [author.get("name", "") for author in item.get("authors", []) if author.get("name")],
                            "pubdate": pubdate_raw,
                            "identifiers": identifiers,
                            "mesh_terms": article_details.get("mesh_terms", []),
                            "abstract_sections": abstract_sections,
                            "abstract_text": " ".join(abstract_sections),
                            "article_types": article_details.get("article_types", []),
                        },
                        gaps=gaps,
                        evidence_label="Abstract excerpt" if abstract_snippet else "Citation summary",
                        evidence_snippet=abstract_snippet or citation_snippet or title,
                        normalized_summary=summary,
                    )
                )
            return records

    def healthcheck(self) -> tuple[bool, str]:
        try:
            with self._build_client(10.0) as client:
                response = client.get(
                    self._search_url,
                    params={"db": "pubmed", "retmode": "json", "retmax": 1, "term": "cancer"},
                )
                response.raise_for_status()
            return True, "PubMed reachable"
        except Exception as exc:
            return False, f"PubMed check failed: {exc}"

    def _parse_pubmed_fetch(self, xml_text: str) -> dict[str, dict[str, Any]]:
        root = ET.fromstring(xml_text)
        articles: dict[str, dict[str, Any]] = {}
        for article in root.findall(".//PubmedArticle"):
            pmid = "".join(article.findtext(".//MedlineCitation/PMID", default="").split())
            if not pmid:
                continue

            abstract_sections: list[str] = []
            for abstract_text in article.findall(".//Abstract/AbstractText"):
                text = " ".join("".join(abstract_text.itertext()).split())
                if not text:
                    continue
                label = abstract_text.attrib.get("Label") or abstract_text.attrib.get("NlmCategory")
                abstract_sections.append(f"{label}: {text}" if label else text)

            mesh_terms = [
                " ".join("".join(node.itertext()).split())
                for node in article.findall(".//MeshHeading/DescriptorName")
                if "".join(node.itertext()).strip()
            ]
            article_types = [
                " ".join("".join(node.itertext()).split())
                for node in article.findall(".//PublicationType")
                if "".join(node.itertext()).strip()
            ]
            identifiers: dict[str, str] = {}
            for article_id in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
                id_type = article_id.attrib.get("IdType")
                value = "".join(article_id.itertext()).strip()
                if id_type and value:
                    identifiers[id_type] = value

            articles[pmid] = {
                "abstract_sections": abstract_sections,
                "mesh_terms": mesh_terms,
                "article_types": article_types,
                "identifiers": identifiers,
            }
        return articles

    def _select_abstract_snippet(self, sections: list[str], search_terms: list[str | None]) -> str | None:
        if not sections:
            return None

        normalized_terms = [term.lower() for term in search_terms if isinstance(term, str) and term.strip()]
        best_section = ""
        best_score = -1
        for section in sections:
            lowered = section.lower()
            score = sum(lowered.count(term.lower()) for term in normalized_terms)
            score += 1 if lowered.startswith("results:") or lowered.startswith("conclusions:") else 0
            if score > best_score:
                best_section = section
                best_score = score

        snippet = best_section or sections[0]
        if len(snippet) <= 500:
            return snippet
        return snippet[:497].rstrip() + "..."

    def _parse_pubmed_date(self, value: str | None) -> datetime | None:
        if not value:
            return None

        cleaned = value.replace("/", " ").replace("-", " ").replace(",", " ")
        parts = [part for part in cleaned.split() if part]
        if not parts:
            return None

        try:
            year = int(parts[0])
        except ValueError:
            return None

        month = 1
        day = 1
        if len(parts) >= 2:
            month_name = parts[1][:3].title()
            month = list(calendar.month_abbr).index(month_name) if month_name in calendar.month_abbr else 1
        if len(parts) >= 3:
            try:
                day = int(parts[2])
            except ValueError:
                day = 1

        try:
            return datetime(year, month, day, tzinfo=timezone.utc)
        except ValueError:
            return None
