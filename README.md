# OncoWatch

**OncoWatch** is a local-first desktop application that helps cancer patients and families monitor relevant new oncology information, organize what may matter, and bring structured, source-backed summaries to their oncology team.

> **Safety disclaimer**
>
> OncoWatch is an information monitoring and summarization tool. It does not determine treatment, trial eligibility, or medical appropriateness. It is not a diagnostic system and not a substitute for an oncologist. Every finding requires clinician review.

## What this MVP includes

- Tauri desktop shell for Mac and Windows packaging
- React + TypeScript desktop UI
- Local FastAPI service with SQLite persistence
- First-run onboarding wizard
- Structured patient profile management
- Source connector abstraction with real and demo connectors
- Local scheduler for daily runs
- Deterministic matching and scoring pipeline
- Source-backed findings feed and trial-focused view
- Local PDF export with report history
- OpenRouter setup, validation, and model selection in-app
- Demo profile + demo findings for contributors and first-time users

## Core product principles

- **Local-first**: patient data stays local by default
- **Non-technical user first**: no terminal required for end users
- **Rules-first, LLM-second**: deterministic filtering before summarization
- **Auditability**: every surfaced item stores source, dates, rationale, cautions, score, and model metadata when used
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
The connector system is real and extensible. The MVP ships with:
- `pubmed_literature` – live PubMed literature search
- `demo_trials` – clean demo/starter clinical trial feed
- `demo_drug_updates` – clean demo/starter drug/safety feed
- `demo_biomarker` – clean demo/starter biomarker feed

The demo connectors are intentionally honest starter connectors so contributors can improve them without rewriting the pipeline.

## End-user flow

1. Install OncoWatch as a normal desktop app
2. Open the app
3. Complete onboarding:
   - learn what OncoWatch is and is not
   - enter patient profile details
   - add OpenRouter API key and test it
   - choose monitoring preferences
   - run the setup health check
4. Review the dashboard and findings
5. Run reports locally and bring them to the oncology visit

## Developer setup

### Prerequisites
- Node.js 20+
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
npm install
npm run dev
```

That runs:
- FastAPI backend on `127.0.0.1:17845`
- Tauri desktop dev shell with the Vite UI

## Packaging strategy

OncoWatch is packaged as a Tauri desktop installer. The frontend is bundled by Tauri, and the Python backend is compiled into a standalone sidecar binary using PyInstaller. Tauri bundles external sidecar binaries via `externalBin`, which keeps the backend invisible to the end user and avoids any separate backend startup step. citeturn306174search0turn491430search1turn491430search2

### Build steps

```bash
npm install
cd backend && pip install -e . pyinstaller && cd ..
npm run build:desktop
```

The sidecar build helper writes the packaged backend binary to `dist-sidecar/`, which Tauri includes in the final app bundle.

## Local storage behavior

OncoWatch creates local app directories automatically on first launch:

- SQLite database
- logs
- reports
- config
- encrypted secret key file

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

## OpenRouter setup

The app explains OpenRouter in plain English, lets the user paste a key, tests the key, and fetches models. OpenRouter uses a Bearer token in the `Authorization` header, and its API base is `https://openrouter.ai/api/v1`. The models endpoint can be queried for available models. citeturn306174search2turn306174search7turn306174search20

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

- Real clinical trial connector using structured public APIs
- Additional drug safety and label connectors
- OS keychain integration for secrets
- Multi-profile households
- Better geographic feasibility scoring
- Stronger audit diffing for changed findings
- Offline evidence caching for selected sources
- Auto-updater channel for packaged releases
