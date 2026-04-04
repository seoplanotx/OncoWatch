from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from sqlalchemy import create_engine, inspect, text

from app.db.base import Base
from app.db.migrations import ensure_schema_up_to_date
from app import models  # noqa: F401


class MigrationTests(unittest.TestCase):
    def test_upgrade_creates_schema_for_new_database(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "oncowatch.sqlite3"
            ensure_schema_up_to_date(f"sqlite:///{db_path}")

            engine = create_engine(f"sqlite:///{db_path}", future=True)
            try:
                tables = set(inspect(engine).get_table_names())
                self.assertIn("patient_profiles", tables)
                self.assertIn("alembic_version", tables)
            finally:
                engine.dispose()

    def test_existing_unversioned_database_is_stamped(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "oncowatch.sqlite3"
            engine = create_engine(f"sqlite:///{db_path}", future=True)
            try:
                Base.metadata.create_all(bind=engine)
            finally:
                engine.dispose()

            ensure_schema_up_to_date(f"sqlite:///{db_path}")

            engine = create_engine(f"sqlite:///{db_path}", future=True)
            try:
                tables = set(inspect(engine).get_table_names())
                with engine.connect() as connection:
                    version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                self.assertIn("alembic_version", tables)
                self.assertEqual(version, "20260403_0001")
            finally:
                engine.dispose()
