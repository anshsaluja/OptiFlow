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

    def replace(self, content):
        (self.log() / "00000000000000000000.json").write_text(content)

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

    def test_missing_directory(self):
        (self.root / TABLES[0]).rename(self.root / "moved")
        with self.assertRaisesRegex(ValueError, "Missing parquet table"):
            verify(self.root, "parquet")

    def test_empty_parquet(self):
        (self.root / TABLES[0] / "part-00000.parquet").write_bytes(b"")
        with self.assertRaisesRegex(ValueError, "Parquet part"):
            verify(self.root, "parquet")

    def test_missing_log(self):
        (self.log() / "00000000000000000000.json").unlink()
        self.log().rmdir()
        with self.assertRaisesRegex(ValueError, "Missing Delta transaction log"):
            verify(self.root, "delta")

    def test_valid_multiple_lines(self):
        self.replace('{"protocol":{}}\n{"add":{"path":"x"}}\n')
        verify(self.root, "delta")

    def test_blank_line(self):
        self.replace('{"add":{}}\n \n')
        with self.assertRaisesRegex(ValueError, "blank Delta action"):
            verify(self.root, "delta")

    def test_multiple_actions(self):
        self.replace('{"add":{},"remove":{}}\n')
        with self.assertRaisesRegex(ValueError, "exactly one"):
            verify(self.root, "delta")

    def test_action_with_extra_key(self):
        self.replace('{"add":{},"unexpected":1}\n')
        with self.assertRaisesRegex(ValueError, "exactly one"):
            verify(self.root, "delta")

    def test_non_object_action(self):
        self.replace('[]\n')
        with self.assertRaisesRegex(ValueError, "exactly one"):
            verify(self.root, "delta")

    def test_null_payload(self):
        self.replace('{"add":null}\n')
        with self.assertRaisesRegex(ValueError, "payload"):
            verify(self.root, "delta")

    def test_scalar_payload(self):
        self.replace('{"add":5}\n')
        with self.assertRaisesRegex(ValueError, "payload"):
            verify(self.root, "delta")


if __name__ == "__main__":
    unittest.main()
