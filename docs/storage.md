# Local storage strategy

OncoWatch creates storage automatically on first launch.

## App directories

The backend uses platform-appropriate user directories and creates:

- `data/` equivalent directory
- `config/` equivalent directory
- `cache/` equivalent directory
- `reports/`
- `logs/`

## Stored locally

### SQLite database
- patient profiles
- findings
- monitoring runs
- report history
- settings
- source configs
- onboarding state

### Config
- generated local secret key used for encrypting API keys at rest

### Reports
- clinician-facing PDF exports

### Logs
- operational logs for debugging and contributor support

## Path shape used by the app

The code centralizes paths in `backend/app/core/paths.py`.

Main outputs:
- database path
- reports directory
- logs directory
- config directory
- secret key path

## Storage principles

- everything is local by default
- no cloud sync in MVP
- no manual file creation required
- folders are created automatically
