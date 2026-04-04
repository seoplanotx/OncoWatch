# Packaging strategy

## Goals

- notarized direct-download DMG for macOS first
- no Python install required for patients
- no manual backend startup
- local SQLite storage
- local report generation

## Runtime packaging approach

### Desktop shell
Tauri is used as the desktop bundler layer and produces the signed `.app` bundle.

### Backend
The FastAPI service is compiled into a standalone binary with PyInstaller.

### Frontend
The React/Vite build is bundled into the Tauri application.

## Why sidecar packaging

Tauri supports bundling external binaries using `externalBin`, which is the cleanest way to ship a non-Rust backend alongside the UI. The app can then spawn the backend as a local child process without exposing backend startup to the end user.

## Build flow

1. Install backend build dependencies with `python -m pip install -e './backend[build]'`
2. Build the backend sidecar binary
3. Build the Tauri macOS app bundle
4. Wrap the `.app` in a DMG with the repo-owned `scripts/build_macos_dmg.sh`

## Installer expectations

### Windows
- MSI / EXE style installer via Tauri bundle target
- backend sidecar included automatically

### macOS
- Tauri builds the `.app` bundle and the repo wraps it into the distributable DMG
- backend sidecar included inside the application bundle
- DMG created with `hdiutil` for non-interactive local/CI builds
- app must be code signed and notarized before distribution

## Update strategy

Not included in MVP. Tauri’s updater plugin can be layered in later without changing the app’s local-first storage design.
