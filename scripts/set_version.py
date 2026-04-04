from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def update_json(path: Path, version: str) -> None:
    payload = json.loads(path.read_text())
    payload["version"] = version
    path.write_text(json.dumps(payload, indent=2) + "\n")


def update_pattern(path: Path, pattern: str, replacement: str) -> None:
    content = path.read_text()
    updated, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"Expected one match in {path}, found {count}")
    path.write_text(updated)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/set_version.py <semver>", file=sys.stderr)
        return 1

    version = sys.argv[1].strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        print("version must look like 1.2.3", file=sys.stderr)
        return 1

    update_json(ROOT / "package.json", version)
    update_json(ROOT / "apps/desktop/package.json", version)
    update_pattern(ROOT / "apps/desktop/src-tauri/Cargo.toml", r'^version = ".*"$', f'version = "{version}"')
    update_pattern(ROOT / "apps/desktop/src-tauri/tauri.conf.json", r'"version": ".*"', f'"version": "{version}"')
    update_pattern(ROOT / "backend/pyproject.toml", r'^version = ".*"$', f'version = "{version}"')
    update_pattern(ROOT / "backend/app/core/release.py", r'^APP_VERSION = ".*"$', f'APP_VERSION = "{version}"')
    print(f"Updated OncoWatch version to {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
