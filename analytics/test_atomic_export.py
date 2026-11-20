"""Atomic CSV publication regression tests for scenario analytics."""
import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scenario_analytics import main


class AtomicCsvExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.output = self.directory / "impact.csv"
        self.output.write_text("previous,complete\n", encoding="utf-8")

    def test_success_replaces_previous_csv_without_temporary_files(self):
        with patch("scenario_analytics.analyze", return_value=(["id", "cost"], [("closure", 12.5)])):
            main(["scenario_analytics.py", str(self.directory), str(self.output)])
        self.assertEqual(self.output.read_text(encoding="utf-8"), "id,cost\nclosure,12.5\n")
        self.assertEqual(list(self.directory.glob(".impact.csv.*.tmp")), [])

    def test_writer_failure_preserves_previous_csv_and_cleans_temp(self):
        with patch("scenario_analytics.analyze", return_value=(["id"], [("closure",)])):
            with patch("scenario_analytics.csv.writer", side_effect=OSError("disk failure")):
                with self.assertRaisesRegex(OSError, "disk failure"):
                    main(["scenario_analytics.py", str(self.directory), str(self.output)])
        self.assertEqual(self.output.read_text(encoding="utf-8"), "previous,complete\n")
        self.assertEqual(list(self.directory.glob(".impact.csv.*.tmp")), [])


    def test_atomic_replace_failure_preserves_existing_csv(self):
        with patch("scenario_analytics.analyze", return_value=(["id"], [("closure",)])):
            with patch("scenario_analytics.os.replace", side_effect=OSError("rename failure")):
                with self.assertRaisesRegex(OSError, "rename failure"):
                    main(["scenario_analytics.py", str(self.directory), str(self.output)])
        self.assertEqual(self.output.read_text(encoding="utf-8"), "previous,complete\n")
        self.assertEqual(list(self.directory.glob(".impact.csv.*.tmp")), [])


    def test_sync_failure_preserves_existing_csv(self):
        with patch("scenario_analytics.analyze", return_value=(["id"], [("closure",)])):
            with patch("scenario_analytics.os.fsync", side_effect=OSError("sync failure")):
                with self.assertRaisesRegex(OSError, "sync failure"):
                    main(["scenario_analytics.py", str(self.directory), str(self.output)])
        self.assertEqual(self.output.read_text(encoding="utf-8"), "previous,complete\n")
        self.assertEqual(list(self.directory.glob(".impact.csv.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
