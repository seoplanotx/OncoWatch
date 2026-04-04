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
- `GET /api/settings` — app settings
- `PUT /api/settings` — update app settings
- `GET /api/settings/provider/openrouter` — provider config
- `POST /api/settings/provider/openrouter/save` — save provider config
- `POST /api/settings/provider/openrouter/test` — validate API key
- `GET /api/settings/provider/openrouter/models` — get model list / fallback list

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
- `GET /api/reports` — report history
- `POST /api/reports/generate` — generate report
- `GET /api/reports/{report_id}/download` — download report PDF
