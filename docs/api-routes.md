# API routes

## Health
- `GET /api/health` — local health check

## Bootstrap / onboarding
- `GET /api/bootstrap` — app version, local directories, privacy/support info, and initial bootstrap state
- `GET /api/onboarding/state` — current onboarding state
- `POST /api/onboarding/complete` — mark onboarding complete after blocking health checks pass
- `POST /api/onboarding/demo-profile` — create the seeded demo profile

## Profiles
- `GET /api/profiles` — list profiles
- `GET /api/profiles/active` — current active/default profile
- `GET /api/profiles/{profile_id}` — fetch one profile
- `POST /api/profiles` — create profile
- `PUT /api/profiles/{profile_id}` — update profile

## Settings / provider
- `GET /api/settings` — app settings (includes `active_ai_provider`)
- `PUT /api/settings` — update app settings (omitting `active_ai_provider` leaves the selection unchanged)
- `GET /api/settings/provider/{provider_key}` — provider config (`openrouter` or `anthropic`; unknown keys 422)
- `POST /api/settings/provider/{provider_key}/save` — save provider config (key encrypted at rest). `selected_model` accepts any model id the provider recognizes, so a user can save an id that is not in the curated/live list (e.g. `moonshotai/kimi-k3`)
- `POST /api/settings/provider/{provider_key}/test` — validate API key against the provider
- `GET /api/settings/provider/{provider_key}/models` — model list (live full catalog when a key is stored, else a curated per-provider fallback spanning the frontier labs). The list is a convenience, not a limit — any valid model id may be entered by hand in the UI
- `GET /api/settings/mcp` — Claude Desktop (MCP) access status (`enabled`, `has_token`; never the token itself)
- `POST /api/settings/mcp/enable` — enable access and return the connection code (shown once; re-calling rotates it)
- `POST /api/settings/mcp/disable` — disable access and clear the stored token

## Sources
- `GET /api/sources` — list source configs
- `PUT /api/sources/{source_id}` — update source enabled/settings state

## Findings
- `GET /api/findings` — list findings with optional filters
- `GET /api/findings/{finding_id}` — finding detail

## Runs
- `GET /api/runs` — monitoring run history
- `POST /api/runs/trigger` — manual monitoring run, returns `409` if another run is already active

## Dashboard
- `GET /api/dashboard` — latest overview and counters

## Reports
- `GET /api/reports` — report history for the active profile, as
  `{items, other_profiles_count}`. Items carry a computed `file_exists`;
  reports whose profile was deleted stay visible in every view.
- `GET /api/reports/preview?report_type=&profile_id=` — what a report would contain, without rendering or storing anything
- `POST /api/reports/generate` — generate report. For `appointment_prep`,
  optional `appointment_date` and `appointment_clinician` are printed on the
  PDF header only — never persisted to the database or audit log.
- `DELETE /api/reports/{report_id}` — remove the history row and delete the
  PDF from disk (`204`; succeeds even if the file is already gone)
- `GET /api/reports/{report_id}/download` — download report PDF

`report_type` is one of `daily_summary`, `full_review`, `appointment_prep`;
anything else is a `422`. Both the preview and the `outline` stored on a
generated report use the same assembly, so the in-app report view and the PDF
always agree. The appointment prep sheet's "Top things to raise" leads with
findings the user saved for discussion (ranked), then backfills with the
highest-priority remaining items up to the cap.

## MCP gateway (Claude Desktop extension)
Read-only, consent-gated namespace used exclusively by the Firstlight Desktop
Extension (`packages/mcp-server`). Every route requires the user-enabled flag
(else `403`) and `Authorization: Bearer <connection code>` (else `401`).
Payloads are privacy projections — public source data plus non-identifying
rationale; case context only as the de-identified packet. See
`docs/mcp-extension.md`.
- `GET /api/mcp/status` — app/monitoring status snapshot
- `GET /api/mcp/findings` — findings projection (`finding_type`, `query`, `limit` filters)
- `GET /api/mcp/findings/{finding_id}` — one finding projection
- `GET /api/mcp/case-context` — de-identified case packet only
- `GET /api/mcp/clinician-summary` — clinician summary with de-identified case context
- `GET /api/mcp/runs` — recent monitoring runs (no error text or internals)
