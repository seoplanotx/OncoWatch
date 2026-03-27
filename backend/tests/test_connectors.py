from __future__ import annotations

from datetime import datetime, timezone
import unittest
from types import SimpleNamespace

import httpx

from app.connectors.base import ConnectorContext
from app.connectors.clinicaltrials_connector import ClinicalTrialsGovConnector
from app.connectors.pubmed_connector import PubMedConnector


def build_profile() -> SimpleNamespace:
    return SimpleNamespace(
        cancer_type="Non-small cell lung cancer",
        subtype="Adenocarcinoma",
        stage_or_context="Metastatic",
        location_label="Dallas-Fort Worth, Texas",
        biomarkers=[
            SimpleNamespace(name="EGFR", variant="Exon 19 deletion"),
            SimpleNamespace(name="TP53", variant=None),
        ],
        therapy_history=[
            SimpleNamespace(therapy_name="Osimertinib", therapy_type="targeted therapy"),
        ],
        would_consider=["clinical trials"],
        would_not_consider=["long-distance travel without a strong rationale"],
    )


def build_context(settings: dict) -> ConnectorContext:
    return ConnectorContext(
        profile=build_profile(),
        source_config=SimpleNamespace(settings_json=settings),
        requested_at=datetime.now(timezone.utc),
    )


class ClinicalTrialsConnectorTests(unittest.TestCase):
    def test_fetch_parses_realistic_study_fields(self) -> None:
        connector = ClinicalTrialsGovConnector()

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/api/v2/studies")
            self.assertEqual(request.url.params["query.cond"], "Non-small cell lung cancer Adenocarcinoma")
            self.assertEqual(request.url.params["pageSize"], "8")
            self.assertIn("EGFR Exon 19 deletion", request.url.params["query.term"])
            body = {
                "studies": [
                    {
                        "protocolSection": {
                            "identificationModule": {
                                "nctId": "NCT12345678",
                                "briefTitle": "EGFR-directed therapy after osimertinib progression",
                            },
                            "statusModule": {
                                "overallStatus": "RECRUITING",
                                "lastUpdatePostDateStruct": {"date": "2026-03-20"},
                            },
                            "descriptionModule": {
                                "briefSummary": "Study for metastatic EGFR-mutated NSCLC after osimertinib resistance.",
                            },
                            "conditionsModule": {
                                "conditions": ["Non-small Cell Lung Cancer"],
                                "keywords": ["EGFR", "Osimertinib resistance"],
                            },
                            "designModule": {"phases": ["PHASE1", "PHASE2"]},
                            "armsInterventionsModule": {
                                "interventions": [
                                    {"name": "Osimertinib", "type": "DRUG"},
                                    {"name": "Amivantamab", "type": "BIOLOGICAL"},
                                ]
                            },
                            "contactsLocationsModule": {
                                "locations": [
                                    {
                                        "facility": "UT Southwestern",
                                        "city": "Dallas",
                                        "state": "Texas",
                                        "country": "United States",
                                        "status": "RECRUITING",
                                    }
                                ]
                            },
                            "sponsorCollaboratorsModule": {
                                "leadSponsor": {"name": "UT Southwestern"}
                            },
                            "eligibilityModule": {
                                "eligibilityCriteria": (
                                    "Inclusion Criteria:\n"
                                    "- Metastatic EGFR-mutated NSCLC\n"
                                    "Exclusion Criteria:\n"
                                    "- Uncontrolled brain metastases"
                                )
                            },
                        }
                    }
                ]
            }
            return httpx.Response(200, json=body)

        connector._build_client = lambda timeout: httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout)  # type: ignore[method-assign]
        context = build_context({"page_size": 8})
        records = connector.fetch(context)

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.external_identifier, "NCT12345678")
        self.assertEqual(record.source_name, "ClinicalTrials.gov")
        self.assertIn("Phase 1", record.summary)
        self.assertIn("Dallas", record.location_summary or "")
        self.assertEqual(record.raw_payload["nct_id"], "NCT12345678")
        self.assertIn("Inclusion Criteria", record.raw_payload["inclusion_excerpt"])
        self.assertEqual(record.evidence_label, "Eligibility criteria excerpt")


class PubMedConnectorTests(unittest.TestCase):
    def test_fetch_prefers_abstract_snippet(self) -> None:
        connector = PubMedConnector()

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/esearch.fcgi"):
                return httpx.Response(200, json={"esearchresult": {"idlist": ["40000001"]}})
            if request.url.path.endswith("/esummary.fcgi"):
                return httpx.Response(
                    200,
                    json={
                        "result": {
                            "uids": ["40000001"],
                            "40000001": {
                                "uid": "40000001",
                                "title": "Resistance pathways after osimertinib in EGFR-mutated NSCLC",
                                "fulljournalname": "Journal of Thoracic Oncology",
                                "pubdate": "2026 Mar 12",
                                "authors": [{"name": "Lee J"}, {"name": "Patel R"}],
                            },
                        }
                    },
                )
            if request.url.path.endswith("/efetch.fcgi"):
                xml = """
                <PubmedArticleSet>
                  <PubmedArticle>
                    <MedlineCitation>
                      <PMID>40000001</PMID>
                      <MeshHeadingList>
                        <MeshHeading><DescriptorName>Carcinoma, Non-Small-Cell Lung</DescriptorName></MeshHeading>
                      </MeshHeadingList>
                      <Article>
                        <Abstract>
                          <AbstractText Label="Results">Patients with EGFR exon 19 deletion had prolonged benefit from osimertinib before MET-mediated resistance emerged.</AbstractText>
                          <AbstractText Label="Conclusions">Updated molecular profiling remained important after progression.</AbstractText>
                        </Abstract>
                      </Article>
                    </MedlineCitation>
                    <PubmedData>
                      <ArticleIdList>
                        <ArticleId IdType="doi">10.1000/example</ArticleId>
                      </ArticleIdList>
                    </PubmedData>
                  </PubmedArticle>
                </PubmedArticleSet>
                """
                return httpx.Response(200, text=xml)
            raise AssertionError(f"Unexpected path: {request.url.path}")

        connector._build_client = lambda timeout: httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout)  # type: ignore[method-assign]
        context = build_context({"retmax": 3})
        records = connector.fetch(context)

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.external_identifier, "PMID:40000001")
        self.assertEqual(record.evidence_label, "Abstract excerpt")
        self.assertIn("EGFR exon 19 deletion", record.evidence_snippet or "")
        self.assertIn("Journal of Thoracic Oncology", record.tags)
        self.assertEqual(record.raw_payload["identifiers"]["doi"], "10.1000/example")
        self.assertFalse(record.gaps)

    def test_fetch_falls_back_when_abstract_missing(self) -> None:
        connector = PubMedConnector()

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/esearch.fcgi"):
                return httpx.Response(200, json={"esearchresult": {"idlist": ["40000002"]}})
            if request.url.path.endswith("/esummary.fcgi"):
                return httpx.Response(
                    200,
                    json={
                        "result": {
                            "uids": ["40000002"],
                            "40000002": {
                                "uid": "40000002",
                                "title": "Review of resistance testing after targeted therapy",
                                "fulljournalname": "Clinical Lung Cancer",
                                "pubdate": "2025 Oct",
                                "authors": [{"name": "Smith A"}],
                            },
                        }
                    },
                )
            if request.url.path.endswith("/efetch.fcgi"):
                return httpx.Response(200, text="<PubmedArticleSet></PubmedArticleSet>")
            raise AssertionError(f"Unexpected path: {request.url.path}")

        connector._build_client = lambda timeout: httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout)  # type: ignore[method-assign]
        context = build_context({"retmax": 1})
        records = connector.fetch(context)

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.evidence_label, "Citation summary")
        self.assertIn("Clinical Lung Cancer", record.evidence_snippet or "")
        self.assertTrue(record.gaps)
        self.assertIn("PubMed did not provide an abstract", record.gaps[0])
