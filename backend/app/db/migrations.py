from __future__ import annotations

from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.paths import get_app_paths


def _script_location() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "alembic"
    return Path(__file__).resolve().parents[2] / "alembic"


def _db_url() -> str:
    return f"sqlite:///{get_app_paths().db_path}"


def build_alembic_config(db_url: str | None = None) -> Config:
    config = Config()
    config.set_main_option("script_location", str(_script_location()))
    config.set_main_option("sqlalchemy.url", db_url or _db_url())
    config.attributes["configure_logger"] = False
    return config


def ensure_schema_up_to_date(db_url: str | None = None) -> None:
    effective_db_url = db_url or _db_url()
    engine = create_engine(effective_db_url, future=True)
    try:
        table_names = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    config = build_alembic_config(effective_db_url)
    if "alembic_version" in table_names:
        command.upgrade(config, "head")
        return

    if table_names:
        command.stamp(config, "head")
        return

    command.upgrade(config, "head")
