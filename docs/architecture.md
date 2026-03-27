# OncoWatch Architecture

## Top-level design

OncoWatch is a **desktop-first local application** with three runtime layers:

1. **Tauri shell**
2. **React UI**
3. **Local FastAPI service**

The UI talks only to the local API. There is no required cloud backend for MVP.

## Why this shape

- Keeps end-user install simple
- Preserves local-first storage
- Lets us build the clinical logic in Python
- Keeps the frontend focused on trust, readability, and report workflows
- Makes future connector growth easier

## Key app modules

### Onboarding
Guided first-run experience that:
- explains scope and disclaimer
- creates the initial patient profile
- configures OpenRouter
- chooses scheduling and report defaults
- runs health checks
- finalizes onboarding

### Profile service
Owns:
- patient profile CRUD
- biomarkers
- therapy history
- structured preferences and exclusions

### Connector service
Owns:
- source registry
- source config lookup
- source execution
- connector-specific normalization

### Matching + scoring
Owns:
- deterministic relevance logic
- structured rationale generation
- confidence and caution classification

### Monitoring job
Owns:
- scheduled or manual run execution
- connector fan-out
- finding persistence
- new/changed detection
- run summaries

### Report service
Owns:
- PDF generation
- report history persistence
- clinician discussion question generation
- evidence appendix formatting

### Settings + secrets
Owns:
- daily run settings
- report defaults
- provider config
- encrypted local secret storage

## Rules-first, LLM-second

The LLM is limited to:
- summarization
- cautious explanation
- discussion-question generation
- missing information prompts

The LLM is not used as the primary relevance engine.

## DB pattern

SQLite with SQLAlchemy models.

Key entities:
- PatientProfile
- Biomarker
- TherapyHistoryEntry
- Finding
- FindingEvidence
- MonitoringRun
- SourceConfig
- ReportExport
- AppSettings
- ApiProviderConfig
- OnboardingState

## Deployment pattern

### Development
- FastAPI launched directly via Python
- Tauri dev shell points to Vite dev server
- React calls local backend on `127.0.0.1:17845`

### Packaged app
- Python backend compiled to a sidecar binary
- Tauri bundles the sidecar and spawns it on app startup
- End user never starts the backend manually
