# Connectors And Matching

## ClinicalTrials.gov connector

The default clinical trial source is now `clinicaltrials_gov`, backed by the ClinicalTrials.gov API v2.

Behavior:
- Builds a trial search from the active profile cancer type, subtype, biomarkers, stage/context, and recent therapy names.
- Uses `page_size` from `SourceConfig.settings_json` and supports an optional `overall_statuses` filter list.
- Parses and stores structured trial fields in `ConnectorRecord.raw_payload`, including:
  - `nct_id`
  - `title`
  - `recruitment_status`
  - `phases`
  - `conditions`
  - `keywords`
  - `interventions`
  - `locations`
  - `sponsor`
  - `study_url`
  - `brief_summary`
  - `eligibility_criteria_excerpt`
  - `inclusion_excerpt`
  - `exclusion_excerpt`
- Uses the ClinicalTrials.gov version endpoint for health checks.

Notes:
- Existing local installs with the old `demo_trials` source are migrated in place to `clinicaltrials_gov`.
- The legacy demo trial connector remains registered so contributor workflows do not hard-fail.
- The public release does not enable demo connectors by default.

## PubMed connector

The PubMed connector now does three calls per run:
- `esearch` for the PMID set
- `esummary` for citation metadata
- `efetch` XML for abstract sections and identifiers

Behavior:
- Search terms are scoped to `Title/Abstract` fields when profile terms are available.
- Evidence snippets prefer abstract sections with the best overlap to the profile query terms.
- When no abstract is available, the connector falls back to a citation-only snippet and records an explicit gap.
- Raw payload includes journal, authors, PubMed identifiers, MeSH terms, article types, and abstract sections when available.

## Normalization and scoring

Matching is still deterministic and local.

The new normalization layer builds:
- profile facts: cancer terms, subtype terms, biomarker phrases, therapy terms, preferences, exclusions, geography terms
- record facts: matched cancer/subtype/biomarker/therapy terms, recruitment status, phase, geography overlap, freshness bucket, abstract availability, identifiers, missing fields

The scoring engine now:
- relies on normalized facts instead of a single substring haystack
- records explicit weighted rules in `match_debug.rules`
- stores `profile_facts`, `record_facts`, and the connector `record_payload` in `match_debug`
- keeps labels conservative:
  - `High relevance`
  - `Worth reviewing`
  - `Low confidence`
  - `Insufficient data`

Trial-specific logic currently emphasizes:
- direct cancer-context match
- biomarker alignment
- recruitment status
- geography overlap
- recent evidence

## Finding change detection

Finding hashes now include:
- summary fields
- evidence snippet/label
- connector raw payload
- normalized summary
- normalized facts

This reduces false "unchanged" results when status, eligibility text, or other structured facts move without a title change.

## Test command

From `backend/`:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
```
