# OncoWatch macOS release checklist

## Toolchain and CI

- `nvm use` so the repo uses Node 22.x from `.nvmrc`
- verify Python 3.11 is active
- verify Rust stable is active
- confirm GitHub Actions passed:
  - backend tests
  - frontend typecheck/build
  - macOS desktop build

## Local verification

- run `npm run lint`
- run `npm run build:frontend`
- run `npm run test:backend`
- run `npm run check:rust`
- run `npm run build:desktop`

## Clean-machine macOS QA

- install the DMG on a clean Mac
- launch the app and confirm the local backend starts
- complete onboarding without any blocking health-check failures
- verify the app clearly says automatic runs only happen while OncoWatch is open
- run a manual monitoring cycle
- generate and download both report types
- open About / Support and confirm data, reports, logs, and config paths render
- quit and reopen the app to confirm local data persists

## Signing and notarization

- sign the app bundle with the release certificate
- sign the DMG if your release flow requires it
- submit the build for notarization
- staple the notarization ticket to the shipped artifact

## Release handoff

- record the shipped version and git commit
- attach known issues and any post-release monitoring notes
- keep the previous signed DMG available for rollback
- include support notes covering log collection and manual reset steps
