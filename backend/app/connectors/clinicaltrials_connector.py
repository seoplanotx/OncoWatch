from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.connectors.base import BaseConnector, ConnectorContext, ConnectorRecord


ACTIVE_RECRUITMENT_STATUSES = [
    "RECRUITING",
    "NOT_YET_RECRUITING",
    "ENROLLING_BY_INVITATION",
    "ACTIVE_NOT_RECRUITING",
]


class ClinicalTrialsGovConnector(BaseConnector):
    key = "clinicaltrials_gov"
    category = "clinical_trials"
    display_name = "ClinicalTrials.gov trials"

    _studies_url = "https://clinicaltrials.gov/api/v2/studies"
    _version_url = "https://clinicaltrials.gov/api/v2/version"

    def _build_client(self, timeout: float) -> httpx.Client:
        return httpx.Client(
            timeout=timeout,
            headers={
                "accept": "application/json",
                "user-agent": "OncoWatch/0.1",
            },
        )

    def _page_size(self, context: ConnectorContext) -> int:
        settings = context.source_config.settings_json or {}
        raw_value = settings.get("page_size", settings.get("retmax", 10))
        try:
            page_size = int(raw_value)
        except (TypeError, ValueError):
            page_size = 10
        return max(1, min(page_size, 25))

    def _overall_statuses(self, context: ConnectorContext) -> list[str]:
        settings = context.source_config.settings_json or {}
        configured = settings.get("overall_statuses")
        if isinstance(configured, list) and configured:
            return [str(item).strip().upper() for item in configured if str(item).strip()]
        return list(ACTIVE_RECRUITMENT_STATUSES)

    def _build_query(self, context: ConnectorContext) -> dict[str, str]:
        profile = context.profile
        condition_terms = [getattr(profile, "cancer_type", None), getattr(profile, "subtype", None)]
        query_cond = " ".join(part.strip() for part in condition_terms if isinstance(part, str) and part.strip())
        if not query_cond:
            query_cond = "cancer"

        term_parts: list[str] = []
        if getattr(profile, "stage_or_context", None):
            term_parts.append(str(profile.stage_or_context).strip())

        for biomarker in getattr(profile, "biomarkers", [])[:4]:
            biomarker_phrase = " ".join(part.strip() for part in [biomarker.name, biomarker.variant] if part and part.strip())
            if biomarker_phrase:
                term_parts.append(biomarker_phrase)
            elif getattr(biomarker, "name", None):
                term_parts.append(str(biomarker.name).strip())

        for therapy in getattr(profile, "therapy_history", [])[:2]:
            if getattr(therapy, "therapy_name", None):
                term_parts.append(str(therapy.therapy_name).strip())

        query: dict[str, str] = {"query.cond": query_cond}
        if term_parts:
            query["query.term"] = " AND ".join(f'"{part}"' for part in term_parts if part)
        return query

    def fetch(self, context: ConnectorContext) -> list[ConnectorRecord]:
        params: dict[str, Any] = {
            **self._build_query(context),
            "format": "json",
            "countTotal": "true",
            "pageSize": self._page_size(context),
        }

        overall_statuses = self._overall_statuses(context)
        if overall_statuses:
            params["filter.overallStatus"] = ",".join(overall_statuses)

        with self._build_client(30.0) as client:
            response = client.get(self._studies_url, params=params)
            response.raise_for_status()
            payload = response.json()

        studies = payload.get("studies", [])
        records: list[ConnectorRecord] = []
        for study in studies:
            parsed = self._parse_study(study)
            if parsed is not None:
                records.append(parsed)
        return records

    def _parse_study(self, study: dict[str, Any]) -> ConnectorRecord | None:
        protocol = study.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        status_module = protocol.get("statusModule", {})
        description_module = protocol.get("descriptionModule", {})
        conditions_module = protocol.get("conditionsModule", {})
        design_module = protocol.get("designModule", {})
        interventions_module = protocol.get("armsInterventionsModule", {})
        contacts_module = protocol.get("contactsLocationsModule", {})
        sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
        eligibility_module = protocol.get("eligibilityModule", {})

        nct_id = (identification.get("nctId") or "").strip()
        if not nct_id:
            return None

        title = (
            identification.get("briefTitle")
            or identification.get("officialTitle")
            or f"ClinicalTrials.gov study {nct_id}"
        ).strip()
        recruitment_status = (status_module.get("overallStatus") or "").strip() or None
        phase_terms = self._format_phases(design_module.get("phases") or [])
        conditions = self._clean_list(conditions_module.get("conditions") or [])
        keywords = self._clean_list(conditions_module.get("keywords") or [])
        interventions = self._format_interventions(interventions_module.get("interventions") or [])
        locations = self._format_locations(contacts_module.get("locations") or [])
        sponsor = ((sponsor_module.get("leadSponsor") or {}).get("name") or "").strip() or None
        brief_summary = self._clean_text(description_module.get("briefSummary"))
        detailed_description = self._clean_text(description_module.get("detailedDescription"))
        eligibility_text = self._clean_text(eligibility_module.get("eligibilityCriteria"))
        inclusion_excerpt, exclusion_excerpt = self._extract_eligibility_excerpts(eligibility_text)

        source_url = f"https://clinicaltrials.gov/study/{nct_id}"
        published_at = self._parse_partial_date(
            ((status_module.get("lastUpdatePostDateStruct") or {}).get("date"))
            or ((status_module.get("studyFirstPostDateStruct") or {}).get("date"))
        )
        display_status = self._display_status(recruitment_status)
        location_summary = self._summarize_locations(locations)

        tags = self._dedupe(
            [
                *conditions[:3],
                *keywords[:2],
                *phase_terms[:2],
                display_status,
                *interventions[:2],
            ]
        )
        gaps: list[str] = []
        if recruitment_status is None:
            gaps.append("ClinicalTrials.gov did not provide a current recruitment status for this study.")
        if not locations:
            gaps.append("ClinicalTrials.gov did not provide site locations for this study.")
        if not eligibility_text:
            gaps.append("ClinicalTrials.gov did not provide inclusion or exclusion criteria text for this study.")

        evidence_label = "Eligibility criteria excerpt" if inclusion_excerpt or exclusion_excerpt else "Study summary"
        evidence_snippet = (
            inclusion_excerpt
            or exclusion_excerpt
            or brief_summary
            or detailed_description
            or f"{display_status or 'Trial status not listed'}. Review the full record for details."
        )
        normalized_summary = self._build_structured_summary(
            status=display_status,
            phases=phase_terms,
            conditions=conditions,
            interventions=interventions,
            sponsor=sponsor,
            locations=locations,
            brief_summary=brief_summary,
        )

        return ConnectorRecord(
            category="clinical_trials",
            title=title,
            source_name="ClinicalTrials.gov",
            source_url=source_url,
            external_identifier=nct_id,
            summary=normalized_summary,
            tags=tags,
            published_at=published_at,
            location_summary=location_summary,
            raw_payload={
                "nct_id": nct_id,
                "title": title,
                "recruitment_status": recruitment_status,
                "phases": phase_terms,
                "conditions": conditions,
                "keywords": keywords,
                "interventions": interventions,
                "locations": locations,
                "sponsor": sponsor,
                "study_url": source_url,
                "brief_summary": brief_summary,
                "detailed_description_excerpt": self._truncate(detailed_description, 900),
                "eligibility_criteria_excerpt": self._truncate(eligibility_text, 900),
                "inclusion_excerpt": inclusion_excerpt,
                "exclusion_excerpt": exclusion_excerpt,
            },
            gaps=gaps,
            evidence_label=evidence_label,
            evidence_snippet=self._truncate(evidence_snippet, 500),
            normalized_summary=normalized_summary,
        )

    def _clean_text(self, value: Any) -> str:
        if not isinstance(value, str):
            return ""
        return " ".join(value.split())

    def _clean_list(self, values: list[Any]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            if not isinstance(value, str):
                continue
            item = " ".join(value.split()).strip()
            if item:
                cleaned.append(item)
        return self._dedupe(cleaned)

    def _format_phases(self, phases: list[Any]) -> list[str]:
        labels = {
            "EARLY_PHASE1": "Early Phase 1",
            "PHASE1": "Phase 1",
            "PHASE2": "Phase 2",
            "PHASE3": "Phase 3",
            "PHASE4": "Phase 4",
            "NA": "Phase not applicable",
        }
        formatted: list[str] = []
        for phase in phases:
            key = str(phase).strip().upper()
            if not key:
                continue
            formatted.append(labels.get(key, key.replace("_", " ").title()))
        return self._dedupe(formatted)

    def _format_interventions(self, interventions: list[dict[str, Any]]) -> list[str]:
        items: list[str] = []
        for intervention in interventions:
            name = self._clean_text(intervention.get("name"))
            if not name:
                continue
            intervention_type = self._clean_text(intervention.get("type"))
            if intervention_type:
                items.append(f"{name} ({intervention_type.title()})")
            else:
                items.append(name)
        return self._dedupe(items)

    def _format_locations(self, locations: list[dict[str, Any]]) -> list[str]:
        formatted: list[str] = []
        for location in locations:
            parts = [
                self._clean_text(location.get("facility")),
                self._clean_text(location.get("city")),
                self._clean_text(location.get("state")),
                self._clean_text(location.get("country")),
            ]
            text = ", ".join(part for part in parts if part)
            status = self._display_status(self._clean_text(location.get("status")).upper() or None)
            if text and status:
                formatted.append(f"{text} [{status}]")
            elif text:
                formatted.append(text)
        return self._dedupe(formatted)

    def _summarize_locations(self, locations: list[str]) -> str | None:
        if not locations:
            return None
        if len(locations) <= 3:
            return "; ".join(locations)
        return "; ".join(locations[:3]) + f"; +{len(locations) - 3} more site(s)"

    def _build_structured_summary(
        self,
        *,
        status: str | None,
        phases: list[str],
        conditions: list[str],
        interventions: list[str],
        sponsor: str | None,
        locations: list[str],
        brief_summary: str,
    ) -> str:
        parts: list[str] = []
        if status:
            parts.append(f"{status} study")
        else:
            parts.append("Clinical study")
        if phases:
            parts.append(", ".join(phases))
        if conditions:
            parts.append(f"Conditions: {', '.join(conditions[:3])}")
        if interventions:
            parts.append(f"Interventions: {', '.join(interventions[:3])}")
        if sponsor:
            parts.append(f"Sponsor: {sponsor}")
        if locations:
            parts.append(f"Sites: {', '.join(locations[:3])}")
        if brief_summary:
            parts.append(self._truncate(brief_summary, 420))
        return ". ".join(part.rstrip(".") for part in parts if part).strip() + "."

    def _extract_eligibility_excerpts(self, text: str) -> tuple[str | None, str | None]:
        if not text:
            return None, None

        lowered = text.lower()
        inclusion_idx = lowered.find("inclusion criteria")
        exclusion_idx = lowered.find("exclusion criteria")

        inclusion_excerpt = None
        exclusion_excerpt = None

        if inclusion_idx >= 0:
            stop_at = exclusion_idx if exclusion_idx > inclusion_idx else len(text)
            inclusion_excerpt = self._truncate(text[inclusion_idx:stop_at], 380)
        if exclusion_idx >= 0:
            exclusion_excerpt = self._truncate(text[exclusion_idx:], 380)

        if inclusion_excerpt is None and exclusion_excerpt is None:
            return self._truncate(text, 380), None
        return inclusion_excerpt, exclusion_excerpt

    def _parse_partial_date(self, value: str | None) -> datetime | None:
        if not value:
            return None
        for candidate in (value, f"{value}-01", f"{value}-01-01"):
            try:
                return datetime.fromisoformat(candidate).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None

    def _display_status(self, value: str | None) -> str | None:
        if not value:
            return None
        return value.replace("_", " ").title()

    def _truncate(self, value: str, limit: int) -> str:
        text = " ".join(value.split()).strip()
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    def _dedupe(self, values: list[str | None]) -> list[str]:
        seen: set[str] = set()
        deduped: list[str] = []
        for value in values:
            if not value:
                continue
            key = value.strip()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(key)
        return deduped

    def healthcheck(self) -> tuple[bool, str]:
        try:
            with self._build_client(10.0) as client:
                response = client.get(self._version_url)
                response.raise_for_status()
                data = response.json()
            timestamp = data.get("dataTimestamp")
            if timestamp:
                return True, f"ClinicalTrials.gov reachable; data timestamp {timestamp}"
            return True, "ClinicalTrials.gov reachable"
        except Exception as exc:
            return False, f"ClinicalTrials.gov check failed: {exc}"
