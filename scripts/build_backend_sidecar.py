from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
DIST_DIR = ROOT / "dist-sidecar"


def has_pyinstaller(python_path: Path) -> bool:
    result = subprocess.run(
        [str(python_path), "-c", "import PyInstaller"],
        cwd=BACKEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def python_executable() -> Path:
    candidates = [
        BACKEND_DIR / ".venv" / "bin" / "python",
        BACKEND_DIR / ".venv" / "Scripts" / "python.exe",
        Path(sys.executable),
    ]
    for path in candidates:
        if path.exists() and has_pyinstaller(path):
            return path
    raise RuntimeError(
        "PyInstaller is not available in a usable Python environment. "
        "Install backend build dependencies with "
        "`python -m pip install -e ./backend[build]`."
    )


def run(cmd: list[str], cwd: Path) -> None:
    print(f"[oncowatch] running: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)


def target_triple() -> str:
    for key in ("TAURI_ENV_TARGET_TRIPLE", "CARGO_BUILD_TARGET", "ONCOWATCH_TARGET_TRIPLE"):
        value = os.getenv(key)
        if value:
            return value

    result = subprocess.run(
        ["rustc", "-vV"],
        check=True,
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        if line.startswith("host: "):
            return line.removeprefix("host: ").strip()
    raise RuntimeError("Unable to determine the Rust target triple for the backend sidecar")


def main() -> None:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    spec_file = BACKEND_DIR / "oncowatch-backend.spec"

    pyinstaller_cmd = [
        str(python_executable()),
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        "oncowatch-backend",
        "--onefile",
        "--add-data",
        f"{BACKEND_DIR / 'alembic'}{os.pathsep}alembic",
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

    suffix = ".exe" if binary_path.suffix == ".exe" else ""
    target_name = f"oncowatch-backend-{target_triple()}{suffix}"
    target_path = DIST_DIR / target_name
    legacy_target_path = DIST_DIR / binary_path.name
    shutil.copy2(binary_path, target_path)
    shutil.copy2(binary_path, legacy_target_path)
    print(f"[oncowatch] backend sidecar copied to {target_path}")


if __name__ == "__main__":
    main()
