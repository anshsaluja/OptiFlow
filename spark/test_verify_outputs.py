"""Filesystem fixture regression tests for Spark output validation."""
import json
import tempfile
import unittest
from pathlib import Path
from verify_outputs import TABLES, verify


class VerifyOutputsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for table in TABLES:
            directory = self.root / table
            directory.mkdir()
            (directory / "part-00000.parquet").write_bytes(b"PAR1")
            log = directory / "_delta_log"
            log.mkdir()
            (log / "00000000000000000000.json").write_text(json.dumps({"add": {"path": "part-00000.parquet"}}) + "\n")

    def log(self):
        return self.root / TABLES[0] / "_delta_log"

    def test_valid_parquet(self):
        verify(self.root, "parquet")

    def test_valid_delta(self):
        verify(self.root, "delta")

    def test_missing_table(self):
        (self.root / TABLES[0] / "part-00000.parquet").unlink()
        with self.assertRaisesRegex(ValueError, "Parquet part"):
            verify(self.root, "parquet")

    def test_unsupported_format(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            verify(self.root, "csv")

    def test_missing_initial_commit(self):
        (self.log() / "00000000000000000000.json").rename(self.log() / "00000000000000000001.json")
        with self.assertRaisesRegex(ValueError, "initial"):
            verify(self.root, "delta")

    def test_gap_in_versions(self):
        (self.log() / "00000000000000000002.json").write_text('{"add":{}}\n')
        with self.assertRaisesRegex(ValueError, "Gap"):
            verify(self.root, "delta")

    def test_empty_commit(self):
        (self.log() / "00000000000000000000.json").write_text("")
        with self.assertRaisesRegex(ValueError, "Invalid Delta"):
            verify(self.root, "delta")

    def test_malformed_json(self):
        (self.log() / "00000000000000000000.json").write_text("{bad}\n")
        with self.assertRaisesRegex(ValueError, "Invalid Delta"):
            verify(self.root, "delta")

    def test_invalid_action(self):
        (self.log() / "00000000000000000000.json").write_text('{"nonsense":true}\n')
        with self.assertRaisesRegex(ValueError, "Invalid Delta"):
            verify(self.root, "delta")

    def test_valid_second_commit(self):
        (self.log() / "00000000000000000001.json").write_text('{"commitInfo":{}}\n')
        verify(self.root, "delta")


if __name__ == "__main__":
    unittest.main()
