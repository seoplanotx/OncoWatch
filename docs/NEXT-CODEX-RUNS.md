# OncoWatch — Next Codex Run Plan

This document sequences the next Codex runs after the first overnight backend-heavy pass.

## Current state after Run 1
Shipped:
- Real `clinicaltrials_gov` connector
- Upgraded PubMed connector with abstract-aware evidence
- New normalization layer
- Improved deterministic matcher
- Stronger finding change detection
- Backend tests + docs

Known gaps / issues:
- Frontend is still visually rough and does not yet fully capitalize on the richer backend data
- Daily-changes workflow is not yet a first-class product path
- Reports likely need restructuring around briefing value
- Onboarding completion can 500 because a datetime is being written into JSON state without serialization
- Demo drug and biomarker feeds are still demo connectors
- Packaging / release flow is not yet fully production-ready
- Repo cleanup still needed (`backend/oncowatch_backend.egg-info/`, docs cleanup, commit hygiene)

## Execution rules
- Use one Codex run at a time in the main repo until stabilization is complete.
- After stabilization, parallelize only via separate git worktrees.
- Each run must end with:
  - code in a coherent state
  - tests/checks run
  - a changelog of shipped / remaining / risks
  - a git commit and push to `origin main` when the run leaves the repo in a coherent, passing state
- Tucker explicitly wants progress pushed as the work advances. Prefer one clean push per coherent run rather than a mess of tiny noisy pushes.

---

## Run 2 — Stabilization + backend/UI integration
**Model/thinking:** Codex, Extra high
**Goal:** make the current backend improvements actually safe and usable.

### Scope
1. Fix onboarding completion 500 (`datetime` in JSON serialization path)
2. Audit onboarding end-to-end and ensure dashboard opens cleanly after setup
3. Surface richer backend fields cleanly in the frontend where low-risk:
   - recruitment status
   - phase
   - sponsor
   - intervention summary
   - stronger evidence snippet display
4. Clean obvious repo noise:
   - remove `backend/oncowatch_backend.egg-info/` from tracked future state
   - add/update `.gitignore` if needed
   - remove bogus generated citation artifacts from docs/README
5. Validate that old demo installs migrate cleanly to `clinicaltrials_gov`
6. Add tests for the onboarding completion bug and any migration logic touched

### Acceptance criteria
- Fresh install onboarding works start to finish
- Dashboard opens without manual DB surgery
- Findings show materially better backend data
- No backend tests regress
- Repo is cleaner than before

---

## Run 3 — Daily briefing productization
**Model/thinking:** Codex, Extra high
**Goal:** turn the app into a daily-use product instead of a generic tool shell.

### Scope
1. Add a clear “What changed since last run?” path on dashboard and/or reports
2. Prioritize display order using deterministic logic:
   - new first
   - changed second
   - open/relevant trials higher
   - fresher evidence higher
3. Add clearer grouped sections:
   - new findings
   - changed findings
   - top trial matches
   - top literature updates
   - confidence blockers / missing info
4. Improve report structure around briefing value rather than broad export dump
5. Add tests for ranking / grouping logic where practical

### Acceptance criteria
- A user can answer “what’s new that may matter?” in under a minute
- Reports feel like briefings, not database exports
- Dashboard prioritization is stable and explainable

---

## Run 4 — UI/UX overhaul
**Model/thinking:** Codex, Extra high
**Goal:** make the app look like a product someone would trust enough to keep opening.

### Scope
1. Redesign visual system:
   - spacing
   - typography
   - card hierarchy
   - navigation polish
   - empty/loading/error states
2. Improve dashboard layout for scanability
3. Improve findings detail page/feed readability
4. Make the onboarding flow feel modern and calm instead of internal-tool rough
5. Improve safety/disclaimer placement so it reassures instead of cluttering
6. Add responsive behavior for smaller laptop windows

### Acceptance criteria
- Visual quality moves from “internal tool” to “credible product MVP”
- Information hierarchy is clear
- Screenshots become presentable to outsiders

### Note
If needed, this run can happen in a separate worktree after Run 3 to reduce backend collision risk.

---

## Run 5 — Connector honesty + roadmap completion
**Model/thinking:** Codex, high or extra high depending scope
**Goal:** remove remaining “fake product” risk.

### Scope
Choose one of these paths and execute cleanly:

### Path A — Make more feeds real
- Replace demo drug updates with a real source
- Replace demo biomarker updates with a real source
- Add health checks / normalization / tests for each

### Path B — Be brutally honest in product scope
- Hide or clearly label demo-only feeds in UI
- Reframe product as trials + literature first
- Adjust copy, onboarding, and docs accordingly

### Acceptance criteria
- No major product promise is misleading
- Either the feeds are real, or the app clearly says what is and is not real

---

## Run 6 — Packaging, install, and release hardening
**Model/thinking:** Codex, high
**Goal:** make the app shippable, not just runnable by developers.

### Scope
1. Validate sidecar backend packaging path end-to-end
2. Fix or document any missing build scripts / packaging steps
3. Smoke test a packaged build if practical
4. Confirm local storage paths, logs, and reports behavior in packaged mode
5. Add release checklist docs

### Acceptance criteria
- A contributor can build the app without guesswork
- Packaging instructions match reality
- No obvious packaging foot-guns remain

---

## Run 7 — Final QA and finish pass
**Model/thinking:** Codex, high
**Goal:** get to “done enough to demo seriously.”

### Scope
1. End-to-end QA pass
2. Fix broken states / sharp edges
3. Tighten copy
4. Remove dead code / stale docs
5. Produce final changelog + outstanding risks list

### Acceptance criteria
- Clean onboarding
- Clean run flow
- Clean dashboard/findings/report path
- Tests passing
- Docs aligned with actual behavior

---

## Parallelization plan (only after Run 2)
If you want speed later, split work via git worktrees:
- **Worktree A:** UI overhaul (Run 4)
- **Worktree B:** daily briefing/reporting (Run 3)
- **Worktree C:** packaging/docs (Run 6)

But do **not** parallelize before stabilization. That’s how you get a repo full of conflicting half-fixes.

## Suggested immediate next move
Launch **Run 2** next. It is the highest-leverage follow-up because it stabilizes the overnight wins, fixes the onboarding bug, and makes the richer backend data visible to users.
