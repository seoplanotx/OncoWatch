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
- the **report outline** (`build_report_outline`) — a structured description of
  what a report contains, applying the same caps and ordering as the PDF
  builders. It backs `GET /api/reports/preview` and is persisted onto each
  generated report as `summary_json.outline`, so the in-app report view and the
  PDF cannot drift apart. Like the rest of `summary_json`, it carries no
  identifying fields.
- the **prep-sheet selection rule** (`_prep_top_items`): findings the user
  saved for discussion lead "Top things to raise" in rank order, then the
  highest-priority remaining items backfill up to the cap. Selection sits on
  top of `rank_findings_for_briefing` — the shared ranking the dashboard uses
  is not altered. Appointment date/clinician passed at generate time are
  printed on the prep PDF only, never persisted.
- per-report deletion (`delete_report`): removes the PDF and the history row,
  and records a `report_deleted` audit event.

The PDF **presentation layer** is deliberately self-contained rather than
inherited from ReportLab's defaults:
- `_styles()` builds a bare `StyleSheet1`. It does **not** use
  `getSampleStyleSheet()`, whose `Heading3`/`Heading4` are Helvetica-BoldOblique —
  that is where bold-italic item titles came from. A test asserts no style uses an
  oblique or italic face.
- `_esc()` wraps every DB-sourced string before it reaches a `Paragraph`.
  `Paragraph` parses mini-HTML, so this is a correctness boundary, not a nicety:
  unescaped `?tab=table&rank=1` renders as `&rank;=1` (a broken URL) and a title
  containing `<...>` silently loses that span.
- `_make_doc()` / `_content_width()` exist because `SimpleDocTemplate` gives its
  `Frame` 6pt of padding on every side. Declared margins are inset by that amount
  so the *visible* margin is the one asked for, and table widths derive from
  `_content_width(doc)`, never `doc.width`.
- `_kv_table()` / `_stat_strip()` size columns from the frame and set
  `hAlign="LEFT"` explicitly — ReportLab defaults a `Table` to CENTER, so an
  over-wide table straddles both margins instead of failing loudly.
- `_numbered_canvas()` is a two-pass canvas (buffer pages, stamp on save) so every
  page can print `Page N of M`; `_draw_page_furniture()` is a pure drawing function
  over a canvas-like object, exercised in tests with a stub.
- Findings, appendix entries, and prep-sheet items are wrapped in `KeepTogether`
  so a title never separates from its metadata across a page break.

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
