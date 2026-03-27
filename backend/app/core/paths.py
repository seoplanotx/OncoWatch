from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from platformdirs import user_cache_dir, user_config_dir, user_data_dir


APP_NAME = "OncoWatch"
APP_AUTHOR = "OncoWatch"


@dataclass(slots=True)
class AppPaths:
    data_dir: Path
    config_dir: Path
    cache_dir: Path
    reports_dir: Path
    logs_dir: Path
    db_path: Path
    secret_key_path: Path


@lru_cache(maxsize=1)
def get_app_paths() -> AppPaths:
    data_dir = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    config_dir = Path(user_config_dir(APP_NAME, APP_AUTHOR))
    cache_dir = Path(user_cache_dir(APP_NAME, APP_AUTHOR))
    reports_dir = data_dir / "reports"
    logs_dir = data_dir / "logs"
    db_path = data_dir / "oncowatch.sqlite3"
    secret_key_path = config_dir / "secrets.key"

    for path in (data_dir, config_dir, cache_dir, reports_dir, logs_dir):
        path.mkdir(parents=True, exist_ok=True)

    return AppPaths(
        data_dir=data_dir,
        config_dir=config_dir,
        cache_dir=cache_dir,
        reports_dir=reports_dir,
        logs_dir=logs_dir,
        db_path=db_path,
        secret_key_path=secret_key_path,
    )
