# Firstlight

*formerly OncoWatch*

[![CI](https://github.com/seoplanotx/firstlight/actions/workflows/ci.yml/badge.svg)](https://github.com/seoplanotx/firstlight/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/seoplanotx/firstlight)](https://github.com/seoplanotx/firstlight/releases/latest)
[![License: AGPL-3.0-only](https://img.shields.io/badge/license-AGPL--3.0--only-blue.svg)](LICENSE)

**Website: [firstlighthq.com](https://firstlighthq.com)** &nbsp;·&nbsp; Free download for macOS & Windows

**Firstlight** is a local-first desktop application that helps cancer patients and families monitor relevant new oncology information, organize what may matter, and bring structured, source-backed summaries to their oncology team.

> **Safety disclaimer**
>
> Firstlight is an information monitoring and summarization tool. It does not determine treatment, trial eligibility, or medical appropriateness. It is not a diagnostic system and not a substitute for an oncologist. Every finding requires clinician review.
>
> How these guarantees are enforced in code — and how to verify them yourself — is documented in [SAFETY.md](SAFETY.md).

## Why "Firstlight"?

Firstlight was built in memory of **Judy Coffey**.

When she was facing colorectal cancer, I built a tool to dig through the research for her — and it surfaced a promising drug combination from recent trials. We brought it to her oncologist, and he agreed it was worth trying. She passed in April 2025, before she could begin.

Firstlight is the public version of what I built for her, so that no other family has to find what matters too late. The name is the promise: first light is when the day's new research lands — and when you sit down with your coffee and, in a few minutes, know what's new for the person you love.

## What this MVP includes

- Tauri desktop shell packaged for macOS and Windows
- React + TypeScript desktop UI
- Local FastAPI service with SQLite persistence (WAL journaling + startup integrity check)
- First-run onboarding wizard
- Structured patient profile management
- Encryption at rest for identifying fields, with the master key in the OS keychain
- Resilient connectors with retry/backoff so one flaky source can't fail a run
- Four live research connectors for the public release: ClinicalTrials.gov, PubMed, openFDA drug updates, and Europe PMC preprints
- Background monitoring with native notifications while Firstlight runs in the menu bar or system tray
- Deterministic matching and scoring pipeline
- Source-backed findings feed and trial-focused view
- Plain-language interface by default, with an optional clinical-terms mode in Settings
- Per-item triage: mark findings to discuss with the care team or set aside ones that are not relevant
- Personalized daily briefing with a guided first run and friendly source status
- Local PDF reports you can read in the app, print, open, or save a copy of, with report history
- Local activity (audit) log plus export-my-data and delete-my-data controls
- About / Support view with local storage paths and recovery steps

## Core product principles

- **Local-first**: patient data stays local by default
- **Non-technical user first**: no terminal required for end users
- **Rules-first**: deterministic filtering and ranking drive the product
- **Auditability**: every surfaced item stores source, dates, rationale, cautions, and score
- **Truthful scope**: the public release only claims what is real today
- **Open-source friendly**: clean folder structure, readable services, extensible connectors

## A note on the rename

The product is now **Firstlight**. The user-facing name, window title, installer, and reports all say Firstlight.

For backward compatibility and to avoid orphaning existing installs, some **internal identifiers intentionally keep the legacy `oncowatch` name**:

- the on-disk data folder (`OncoWatch`) and database file (`oncowatch.sqlite3`)
- the `ONCOWATCH_*` development environment variables
- the OS-keychain service that stores the master encryption key
- the `ai.oncowatch.desktop` bundle identifier and the packaged `oncowatch-backend` sidecar

Renaming those safely requires a data/key migration step and is tracked as a follow-up.

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

### Privacy modes
Firstlight supports two privacy modes:

- **Mode 1 — Local-only**: patient context stays on-device and no AI provider receives case context.
- **Mode 2 — De-identified AI assist**: identifying details stay local; only minimized oncology context can be sent to a selected AI provider for summaries and briefing questions after explicit disclosure acknowledgement.

See `docs/privacy-modes.md` for the de-identification boundary and allowed/blocked AI payload categories.

### Use with Claude Desktop (optional)

Firstlight ships a [Claude Desktop extension](packages/mcp-server/) — a local,
read-only MCP connection you switch on in Settings. Claude can then answer
questions about the findings Firstlight surfaced, using only public source
data and a de-identified case outline; identifying details never cross the
boundary (enforced in code — see [SAFETY.md](SAFETY.md) and
[docs/mcp-extension.md](docs/mcp-extension.md)).

### Connector strategy
The public release ships with four live connectors:
- `clinicaltrials_gov` – live ClinicalTrials.gov trial search
- `pubmed_literature` – live PubMed literature search with abstract-aware evidence snippets
- `openfda_drug_updates` – live openFDA drug label and safety updates
- `europepmc_preprints` – live Europe PMC preprint and literature search

Contributor-only demo connectors still exist behind the explicit `backend/scripts/seed_demo.py` path for development, but they are not part of the public product scope.
See `docs/connectors-and-matching.md` for connector behavior, normalization, scoring, and test details.

## End-user flow

1. Install Firstlight as a normal desktop app
2. Open the app
3. Complete onboarding:
   - learn what Firstlight is and is not
   - enter patient profile details
   - choose monitoring preferences
   - run the setup health check
4. Review the dashboard and findings
5. Start a manual run
6. Keep Firstlight running in the menu bar or system tray for automatic background monitoring and notifications
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
npm run test:frontend
npm run test:privacy      # de-identification + LLM guardrail suite (see SAFETY.md)
npm run check:rust
npm run test:e2e
```

## Packaging strategy

Firstlight is packaged as a Tauri desktop installer. The frontend is bundled by Tauri, and the Python backend is compiled into a standalone sidecar binary using PyInstaller. Tauri bundles external sidecar binaries via `externalBin`, which keeps the backend invisible to the end user and avoids any separate backend startup step. The repo then wraps the generated macOS `.app` in a deterministic `hdiutil`-based DMG step instead of relying on Finder automation.

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

Firstlight creates local app directories automatically on first launch:

- SQLite database
- logs
- reports
- config
- encrypted secret key file

The public release exposes these paths in the in-app About / Support page. For backward compatibility, the on-disk folder is still named `OncoWatch`.

See `docs/storage.md` for details.

## Development-only environment variables

The desktop app does **not** require users to edit environment files.

The backend reads these only in development (legacy `ONCOWATCH_*` names retained for compatibility):

```text
ONCOWATCH_ENV=development
ONCOWATCH_BACKEND_HOST=127.0.0.1
ONCOWATCH_BACKEND_PORT=17845
ONCOWATCH_OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
ONCOWATCH_ANTHROPIC_BASE_URL=https://api.anthropic.com
```

## Reports

Three report types are included:
- **Daily Summary Report**
- **Full Oncology Review Report**
- **Appointment Prep Sheet** — one page, built to hand to a clinician

Reports are generated locally and saved to the user's app report directory.
Before creating one, Firstlight shows exactly what will be in it; afterwards you
can read the whole report in the app, open the PDF in your usual viewer, print
it, save a copy wherever you like, or remove it. Nothing is uploaded.

The Appointment Prep Sheet leads with the findings you saved for discussion,
then fills remaining space with the highest-priority items, and can carry the
visit date and doctor's name on its header (printed on the sheet only — never
stored in the database).

Each report includes:
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

Firstlight never presents:
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

The full safety design — the de-identification boundary, the fail-closed output validators, encryption at rest — is documented in [SAFETY.md](SAFETY.md), including how to verify it with `npm run test:privacy`.

## License

Firstlight is open source under the **GNU Affero General Public License v3.0 (AGPL-3.0-only)** — see [LICENSE](LICENSE).

What that means in practice:

- You are free to use, study, modify, and share Firstlight.
- If you distribute a modified version, or **run a modified version as a network service**, you must release your source code under the same license.
- This keeps Firstlight — and every derivative of it — open for the families it was built for.

Copyright © 2026 Tucker Coffey.

One exception: the Claude Desktop extension in [`packages/mcp-server/`](packages/mcp-server/) is licensed **Apache-2.0** so it can be adopted and redistributed without AGPL obligations.

**Commercial licensing:** organizations that want to build on Firstlight without AGPL obligations (for example, a hosted or proprietary offering) can contact the copyright holder about a separate commercial license.

## Future roadmap

- Internal rename pass: migrate storage folder, env vars, keychain entry, and bundle identifier off the legacy `oncowatch` name with a safe data/key migration
- Deeper trial feasibility filters for geography and status edge cases
- Additional drug safety and label connectors
- Multi-profile households
- Better geographic feasibility scoring
- Stronger audit diffing for changed findings
- Offline evidence caching for selected sources
