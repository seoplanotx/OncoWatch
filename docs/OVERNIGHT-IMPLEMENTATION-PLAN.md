# OncoWatch — Overnight Implementation Plan

## Objective
Turn OncoWatch from a well-structured MVP shell into a product with real user value by replacing fake data paths, improving evidence quality, and tightening the matching engine around structured facts.

## Strategic thesis
The fastest path to usefulness is **not** more UI polish. It is:
1. real clinical trial data,
2. richer literature evidence,
3. structured normalization before scoring,
4. a more trustworthy deterministic relevance engine,
5. a focused “what changed since yesterday?” briefing.

## Product wedge
Do **not** try to solve all oncology monitoring at once.
Focus the app around a single-profile daily briefing workflow:

> What changed since the last run that may be worth discussing with the oncology team?

That becomes the core promise.

## Phase plan

### Phase 1 — Make the data real

#### 1. Replace demo trial feed with a real ClinicalTrials.gov connector
**Goal:** ship actual structured clinical trial ingestion.

**Deliverables**
- New connector using ClinicalTrials.gov API v2
- Query built from profile cancer type, subtype, and biomarkers
- Parsed fields stored in `ConnectorRecord.raw_payload` and surfaced into finding metadata:
  - NCT id
  - title
  - recruitment status
  - phase
  - conditions
  - interventions
  - locations/sites
  - sponsor
  - study URL
  - inclusion/exclusion snippets when available
- Configurable result limit in source settings
- Health check support

**Acceptance criteria**
- Trial connector returns real records for a demo profile
- Existing run pipeline stores findings without breaking report generation
- Trial findings display enough structured info to be meaningfully reviewed

#### 2. Upgrade PubMed connector from summary-only to abstract-aware
**Goal:** make literature findings worth reading.

**Deliverables**
- Pull article abstracts/snippets, not just summary metadata
- Preserve journal, authors, pub date, identifiers, URL
- Include evidence snippet from abstract or abstract section
- Add fallback behavior when abstract is unavailable

**Acceptance criteria**
- Literature findings contain materially better summaries/evidence than current journal-only snippets
- Reports show useful evidence text instead of hollow metadata

### Phase 2 — Improve matching trustworthiness

#### 3. Introduce normalized matching facts
**Goal:** stop scoring unstructured blobs.

**Deliverables**
- Add a normalization step that extracts structured facts from connector records before scoring
- Proposed normalized fields:
  - cancer terms
  - subtype terms
  - biomarker terms
  - therapy terms
  - recruiting/open status
  - phase
  - geography terms
  - evidence freshness
  - source type
- Use deterministic extraction only for now

**Acceptance criteria**
- Matching service consumes normalized fields rather than a single text haystack for key decisions
- `match_debug` becomes more interpretable

#### 4. Rewrite relevance scoring around explicit rules
**Goal:** make results more defensible.

**Deliverables**
- Replace loose substring-heavy scoring with weighted structured rules
- Explicit reasons for:
  - why it surfaced
  - why it may not fit
  - what information is missing
- Trial-specific logic for recruitment + geography + biomarker alignment
- Freshness boost for recent evidence
- More conservative default labels

**Acceptance criteria**
- Match results are easier to explain and inspect
- False-positive risk is reduced versus current broad matching

### Phase 3 — Improve the user-facing output

#### 5. Add a “Daily Changes” briefing path
**Goal:** emphasize the one job users actually care about.

**Deliverables**
- Dashboard or report view focused on:
  - newly surfaced items
  - changed items
  - highest-signal trial items
  - highest-signal literature/drug updates
  - key missing info
- Reuse existing report system where possible

**Acceptance criteria**
- A user can open the app and quickly answer: “What’s new that may matter?”

### Phase 4 — Stabilize

#### 6. Add tests around the critical path
**Goal:** stop silently breaking trust.

**Minimum test coverage**
- ClinicalTrials.gov connector parsing
- PubMed abstract retrieval parsing
- Matching service scoring behavior
- Finding upsert new/changed detection
- Health check and report smoke tests

**Acceptance criteria**
- Core logic has regression coverage
- Overnight changes can be validated locally

## Overnight execution scope
The realistic overnight target is:

### Must ship tonight
1. Real ClinicalTrials.gov connector
2. Better PubMed evidence retrieval
3. First-pass normalization helpers
4. Safer scoring improvements
5. Tests for new connectors + matching critical path

### Nice if time allows
6. Daily changes report/view improvements
7. Better finding display metadata in UI

### Explicitly out of scope tonight
- Full redesign
- OS keychain integration
- Multi-profile households
- cloud sync
- auto-updater
- broad cancer-type expansion strategy

## Recommended implementation order
1. Add ClinicalTrials.gov connector
2. Wire it into registry + bootstrap default config
3. Upgrade PubMed connector
4. Add normalized fact extraction helpers
5. Refactor matching service to use normalized facts
6. Add tests for connectors and matching
7. Tighten report content if time remains

## Engineering notes
- Preserve local-first behavior
- Keep the LLM out of primary matching logic
- Avoid introducing hidden “AI says so” ranking
- Prefer deterministic logic and explicit audit fields
- Do not break onboarding, scheduler, reports, or existing demo flow
- If a live connector is unavailable or rate-limited, fail gracefully and surface a useful error in health/status

## Definition of a good overnight outcome
By morning, OncoWatch should be able to:
- pull **real trials**,
- pull **better literature evidence**,
- produce **more defensible relevance scoring**,
- and leave the repo in a cleaner, better-tested state.

That is enough to move it from “pretty MVP” to “starting to become real.”

---

## Continuous build queue — keep working until tomorrow afternoon
After the overnight must-ship items are complete, continue down this queue in order. The rule is simple: keep taking the next highest-leverage item that can be completed cleanly without destabilizing the app.

### Priority A — Core product truthfulness
These items increase real-world trust and reduce “demo-ware” risk.

#### A1. Improve finding detail fidelity
**Goal:** every important finding should carry enough structured context to justify its existence.

**Deliverables**
- Extend finding persistence or display helpers to expose more structured trial metadata:
  - trial phase
  - recruiting status
  - sponsor
  - intervention names
  - condition labels
  - site/location summary
- Improve literature finding evidence formatting:
  - abstract snippet
  - journal
  - authors
  - publication date
- Ensure reports include the most decision-relevant metadata first

**Acceptance criteria**
- A user can tell *why* a finding matters without opening raw payload JSON

#### A2. Better changed-item detection and summarization
**Goal:** make “changed” mean something useful.

**Deliverables**
- Improve content hashing inputs so meaningful source changes are captured while noisy fields do not create false change churn
- Add explicit changed/new labeling for reports and dashboard summaries
- Store or expose a concise explanation of what changed when practical

**Acceptance criteria**
- Re-running the same connector data does not generate noisy false “changed” findings
- Meaningful updates are clearly surfaced as changed items

#### A3. Tighten safety phrasing in reports and UI copy
**Goal:** make the product more trustworthy without sounding robotic.

**Deliverables**
- Review user-facing copy for medical-adjacent overreach
- Use language like:
  - may be relevant
  - worth discussing
  - possible fit based on entered data
  - insufficient information to determine fit
- Avoid accidental implication of eligibility, recommendation, or ranking certainty

### Priority B — Daily briefing workflow
These items sharpen the app around the one job that matters.

#### B1. Add a “What changed since the last run?” summary path
**Goal:** make the latest run instantly useful.

**Deliverables**
- Add a focused summary to the dashboard and/or reports for:
  - new findings
  - changed findings
  - highest-signal trials
  - highest-signal literature/drug updates
  - missing data that blocks confidence
- Keep it brief and scannable

**Acceptance criteria**
- A user can answer “what’s new that may matter?” in under a minute

#### B2. Improve sorting and prioritization of findings
**Goal:** show the most actionable items first.

**Deliverables**
- Sort findings using deterministic priorities such as:
  - status (new/changed first)
  - relevance label
  - score
  - freshness
  - trial recruitment openness
- Keep the sort auditable and stable

**Acceptance criteria**
- High-signal, fresh items naturally rise to the top

### Priority C — Contributor/developer stability
These items prevent the repo from turning into a fragile mess.

#### C1. Add a test harness for connectors and matching
**Goal:** make future iteration safer.

**Deliverables**
- Add or improve pytest setup
- Add fixture-driven tests for connector parsing and normalization
- Add scoring tests that prove conservative behavior
- Add tests for finding upsert state transitions: new / unchanged / changed

#### C2. Add documentation for real connectors and data assumptions
**Goal:** future contributors should not have to reverse-engineer the logic.

**Deliverables**
- Connector docs for ClinicalTrials.gov and PubMed behavior
- Notes on rate limits, fallbacks, and incomplete data conditions
- Matching docs describing how normalization and weights work

#### C3. Add migration strategy notes
**Goal:** future schema changes should not become silent breakage.

**Deliverables**
- Document the current schema limitations
- Recommend or scaffold a migration path (Alembic or equivalent) if feasible without destabilizing MVP
- If full migration setup is too large, at least leave clear technical debt notes and boundaries

### Priority D — Stretch work if core is already solid
Only do these if A–C are in good shape.

#### D1. Better geography feasibility logic
- Normalize location/site text more intelligently
- Distinguish local, in-state, out-of-state, and remote/prescreening when possible

#### D2. More explicit evidence freshness indicators
- Add “published recently” logic
- Surface freshness in finding metadata and reports

#### D3. Improve reports from “comprehensive” to “briefing-grade”
- Shorten boilerplate
- Put highest-value items first
- Make clinician discussion questions more tightly tied to surfaced findings

---

## Work sequencing through tomorrow afternoon

### Overnight block
1. Real ClinicalTrials.gov connector
2. Better PubMed evidence retrieval
3. Normalization layer
4. Improved matching rules
5. Critical path tests

### Early-morning block
6. Finding detail fidelity improvements
7. Better changed-item detection
8. Dashboard/report prioritization improvements

### Late-morning to afternoon block
9. Daily changes summary path
10. Documentation pass
11. Additional tests and cleanup
12. Safe stretch improvements only if the core path is stable

---

## Operating rules for continuous execution
- Always leave the repo in a runnable state after each milestone.
- Prefer finishing one coherent vertical slice over scattering partial work everywhere.
- If a feature requires touching UI, backend, and docs, complete the thin end-to-end version before expanding it.
- Run relevant tests/checks after each substantial milestone.
- If blocked on a large task, take the next task that preserves forward momentum rather than stalling.
- Do not invent clinical certainty where source data is incomplete.
- Do not push to GitHub unless explicitly instructed.

## Stop conditions
Pause or downgrade scope if any of the following become true:
- onboarding breaks
- reports stop generating
- runs stop persisting findings correctly
- matching becomes harder to audit than before
- test failures accumulate faster than progress

If a stop condition occurs, stabilize first. Fancy features can wait.

## Definition of a good outcome by tomorrow afternoon
By tomorrow afternoon, OncoWatch should ideally have:
- a **real trials connector**,
- **meaningfully improved literature evidence**,
- a **structured and more defensible matcher**,
- a clearer **daily changes briefing workflow**,
- stronger **tests/docs**,
- and a repo that still feels coherent instead of hacked together.

That would make it substantially closer to a product someone could trust enough to keep using.
