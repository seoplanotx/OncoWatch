from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
DIST_DIR = ROOT / "dist-sidecar"


def run(cmd: list[str], cwd: Path) -> None:
    print(f"[oncowatch] running: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> None:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    spec_file = BACKEND_DIR / "oncowatch-backend.spec"

    pyinstaller_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        "oncowatch-backend",
        "--onefile",
        "--paths",
        str(BACKEND_DIR),
        str(BACKEND_DIR / "app" / "serve.py"),
    ]

    run(pyinstaller_cmd, BACKEND_DIR)

    built_binary_dir = BACKEND_DIR / "dist"
    candidates = [
        built_binary_dir / "oncowatch-backend",
        built_binary_dir / "oncowatch-backend.exe",
    ]
    binary_path = next((path for path in candidates if path.exists()), None)
    if binary_path is None:
        raise FileNotFoundError("Unable to locate packaged backend binary in backend/dist")

    target_path = DIST_DIR / binary_path.name
    shutil.copy2(binary_path, target_path)
    print(f"[oncowatch] backend sidecar copied to {target_path}")


if __name__ == "__main__":
    main()
