# Packaged-app smoke checklist (Firstlight)

Run this on a **clean machine** for each public release (macOS DMG and Windows NSIS).

## Preflight
- [ ] CI green on the release tag
- [ ] Version bumped consistently (root `package.json`, Tauri conf, `APP_VERSION`)
- [ ] Changelog / release notes list known issues

## Install + boot
- [ ] Install artifact without developer tools installed
- [ ] App launches; local backend starts (no terminal)
- [ ] Onboarding completes without blocking on external source downtime
- [ ] Support page shows data/log/report paths

## Core product path
- [ ] Create/edit patient profile
- [ ] Manual “Check now” run completes
- [ ] Dashboard shows new/changed sections OR an honest empty state
- [ ] “Where we looked” shows per-source ok/trouble
- [ ] Findings list triage (discuss / set aside) works, including bulk actions
- [ ] Clinician summary + printable report generate
- [ ] Export my data / delete my data controls work

## Reports (native shell paths — jsdom/Playwright cannot cover these)
- [ ] Save 1–2 findings to discuss; the prep-sheet preview leads with them ("You saved this")
- [ ] Enter appointment date + doctor; the generated PDF header reads "Prepared for the appointment …"
- [ ] **Open PDF** opens the report in the OS default viewer
- [ ] **Show in Finder / File Explorer** selects the file itself, not just the folder
- [ ] **Save a copy…** shows the native dialog and writes a working PDF to the chosen location (try Desktop)
- [ ] **Print** produces a sane print preview of the report contents
- [ ] Delete the PDF from the reports folder; the history row degrades to "no longer on your computer" with **Make it again**
- [ ] **Remove…** deletes the row and the PDF after the in-app confirmation

## Trust / safety
- [ ] Disclaimer visible
- [ ] No demo feeds or demo findings in a default install
- [ ] Privacy mode defaults to local-only
- [ ] Identifying fields not readable as plain text in SQLite

## Packaging-specific
- [ ] Quit and relaunch; data persists
- [ ] Sidecar backend still serves after relaunch
- [ ] (When updater keys live) previous version can detect this release

## Sign-off
- Build version: ________
- Git SHA: ________
- Tester: ________
- Date: ________
- Result: pass / fail (notes): ________
