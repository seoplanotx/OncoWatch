# OncoWatch

**OncoWatch** is a local-first desktop application that helps cancer patients and families monitor relevant new oncology information, organize what may matter, and bring structured, source-backed summaries to their oncology team.

> **Safety disclaimer**
>
> OncoWatch is an information monitoring and summarization tool. It does not determine treatment, trial eligibility, or medical appropriateness. It is not a diagnostic system and not a substitute for an oncologist. Every finding requires clinician review.

## What this MVP includes

- Tauri desktop shell for macOS-first packaging
- React + TypeScript desktop UI
- Local FastAPI service with SQLite persistence
- First-run onboarding wizard
- Structured patient profile management
- Real ClinicalTrials.gov and PubMed connectors for the public release
- Local scheduling while the app is open
- Deterministic matching and scoring pipeline
- Source-backed findings feed and trial-focused view
- Local PDF export with report history
- About / Support view with local storage paths and recovery steps

## Core product principles

- **Local-first**: patient data stays local by default
- **Non-technical user first**: no terminal required for end users
- **Rules-first**: deterministic filtering and ranking drive the product
- **Auditability**: every surfaced item stores source, dates, rationale, cautions, and score
- **Truthful scope**: the public release only claims what is real today
- **Open-source friendly**: clean folder structure, readable services, extensible connectors

## Repo layout

```text
oncowatch/
  apps/
    desktop/               # Tauri + React desktop app
  backend/                 # FastAPI local service + SQLite models + jobs
  docs/                    # Architecture, packaging, storage notes
  docker/                  # Dev-only Docker helpers
  scripts/                 # Build helpers, sidecar packaging
```

## Architecture summary

### Desktop
- **Shell**: Tauri
- **Frontend**: React + TypeScript + Vite
- **Runtime pattern**: UI talks to a local FastAPI service over `http://127.0.0.1:17845`

### Local backend
- **API**: FastAPI
- **DB**: SQLite
- **Scheduler**: APScheduler
- **Reports**: ReportLab PDF generation
- **Secrets**: encrypted locally at rest with a generated machine-local key file

### Connector strategy
The public release ships with:
- `clinicaltrials_gov` – live ClinicalTrials.gov trial search
- `pubmed_literature` – live PubMed literature search with abstract-aware evidence snippets

Contributor-only demo connectors still exist behind the explicit `backend/scripts/seed_demo.py` path for development, but they are not part of the public product scope.
See `docs/connectors-and-matching.md` for connector behavior, normalization, scoring, and test details.

## End-user flow

1. Install OncoWatch as a normal desktop app
2. Open the app
3. Complete onboarding:
   - learn what OncoWatch is and is not
   - enter patient profile details
   - choose monitoring preferences
   - run the setup health check
4. Review the dashboard and findings
5. Start a manual run
6. Optionally leave the app open for while-open automatic runs
7. Run reports locally and bring them to the oncology visit

## Developer setup

### Prerequisites
- Node.js 22.x (`.nvmrc` is included)
- Python 3.11+
- Rust stable toolchain
- Tauri desktop prerequisites for your OS

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

### Frontend / desktop

```bash
nvm use
npm install
npm run dev
```

### Backend tests

```bash
cd backend
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
```

Useful local checks:

```bash
npm run lint
npm run build:frontend
npm run check:rust
npm run test:e2e
```

## Packaging strategy

OncoWatch is packaged as a Tauri desktop installer. The frontend is bundled by Tauri, and the Python backend is compiled into a standalone sidecar binary using PyInstaller. Tauri bundles external sidecar binaries via `externalBin`, which keeps the backend invisible to the end user and avoids any separate backend startup step. The repo then wraps the generated macOS `.app` in a deterministic `hdiutil`-based DMG step instead of relying on Finder automation.

### Build steps

```bash
nvm use
npm install
python -m pip install -e './backend[build]'
npm run build:desktop
```

The sidecar build helper writes the packaged backend binary to `dist-sidecar/`, which Tauri includes in the final app bundle.
See `docs/release-checklist.md` for the macOS signing, notarization, and release handoff flow.

## Local storage behavior

OncoWatch creates local app directories automatically on first launch:

- SQLite database
- logs
- reports
- config
- encrypted secret key file

The public release exposes these paths in the in-app About / Support page.

See `docs/storage.md` for details.

## Development-only environment variables

The desktop app does **not** require users to edit environment files.

The backend reads these only in development:

```text
ONCOWATCH_ENV=development
ONCOWATCH_BACKEND_HOST=127.0.0.1
ONCOWATCH_BACKEND_PORT=17845
ONCOWATCH_OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

## PDF export

Two report types are included:
- **Daily Summary Report**
- **Full Oncology Review Report**

Reports are generated locally and saved to the user’s app report directory. Each report includes:
- patient profile snapshot
- new or changed items
- possible trial matches
- research / drug updates
- why items surfaced
- why they may not fit
- missing information / data gaps
- clinician discussion questions
- disclaimer
- evidence appendix

## Safety guardrails

OncoWatch never presents:
- treatment decisions
- trial eligibility certainty
- “best treatment” rankings
- diagnostic claims

Default language stays cautious:
- may be relevant
- worth discussing with your oncology team
- possible fit based on currently entered profile data
- requires clinician review
- insufficient information to determine fit

## Future roadmap

- Deeper trial feasibility filters for geography and status edge cases
- Additional drug safety and label connectors
- OS keychain integration for secrets
- Multi-profile households
- Better geographic feasibility scoring
- Stronger audit diffing for changed findings
- Offline evidence caching for selected sources
- Auto-updater channel for packaged releases
