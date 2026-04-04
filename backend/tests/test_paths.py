from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from app.core.paths import get_app_paths


class AppPathsTests(unittest.TestCase):
    def setUp(self) -> None:
        get_app_paths.cache_clear()

    def tearDown(self) -> None:
        for key in ("ONCOWATCH_DATA_DIR", "ONCOWATCH_CONFIG_DIR", "ONCOWATCH_CACHE_DIR"):
            os.environ.pop(key, None)
        get_app_paths.cache_clear()

    def test_uses_environment_overrides_for_local_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            os.environ["ONCOWATCH_DATA_DIR"] = str(root / "data")
            os.environ["ONCOWATCH_CONFIG_DIR"] = str(root / "config")
            os.environ["ONCOWATCH_CACHE_DIR"] = str(root / "cache")

            paths = get_app_paths()

            self.assertEqual(paths.data_dir, root / "data")
            self.assertEqual(paths.config_dir, root / "config")
            self.assertEqual(paths.cache_dir, root / "cache")
            self.assertTrue(paths.reports_dir.exists())
            self.assertTrue(paths.logs_dir.exists())


if __name__ == "__main__":
    unittest.main()
