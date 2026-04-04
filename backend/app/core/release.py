from __future__ import annotations

APP_NAME = "OncoWatch"
APP_VERSION = "0.1.0"
MONITORING_MODE = "while_open"
PRODUCT_SCOPE = "ClinicalTrials.gov trials and PubMed literature"
PRIVACY_SUMMARY = "Profiles, reports, logs, and settings stay on this Mac unless you choose to share them."

PUBLIC_SOURCE_KEYS = frozenset({
    "clinicaltrials_gov",
    "pubmed_literature",
})
PUBLIC_SOURCE_CATEGORIES = frozenset({
    "clinical_trials",
    "literature",
})
DEMO_SOURCE_KEYS = frozenset({
    "demo_trials",
    "demo_drug_updates",
    "demo_biomarker",
})
DEMO_FINDING_SOURCE_NAMES = frozenset({
    "OncoWatch Demo Trial Feed",
    "OncoWatch Demo Drug Feed",
    "OncoWatch Demo Biomarker Feed",
})
