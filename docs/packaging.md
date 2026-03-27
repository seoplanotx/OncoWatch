# Packaging strategy

## Goals

- normal desktop installer for Mac and Windows
- no Python install required for patients
- no manual backend startup
- local SQLite storage
- local report generation

## Runtime packaging approach

### Desktop shell
Tauri is used as the installer/bundler layer.

### Backend
The FastAPI service is compiled into a standalone binary with PyInstaller.

### Frontend
The React/Vite build is bundled into the Tauri application.

## Why sidecar packaging

Tauri supports bundling external binaries using `externalBin`, which is the cleanest way to ship a non-Rust backend alongside the UI. The app can then spawn the backend as a local child process without exposing backend startup to the end user. citeturn306174search0turn491430search1turn491430search2

## Build flow

1. Install backend dependencies
2. Build the backend sidecar binary
3. Build the frontend
4. Run `tauri build`
5. Produce platform installers

## Installer expectations

### Windows
- MSI / EXE style installer via Tauri bundle target
- backend sidecar included automatically

### macOS
- app bundle / DMG via Tauri bundle target
- backend sidecar included inside the application bundle

## Update strategy

Not included in MVP. Tauri’s updater plugin can be layered in later without changing the app’s local-first storage design. citeturn491430search6
