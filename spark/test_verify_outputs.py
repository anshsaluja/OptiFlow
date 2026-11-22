"""Filesystem fixture regression tests for Spark output validation."""
import json
import struct
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
            metadata = b"\x00"
            (directory / "part-00000.parquet").write_bytes(b"PAR1" + metadata + struct.pack("<I", len(metadata)) + b"PAR1")
            log = directory / "_delta_log"
            log.mkdir()
            (log / "00000000000000000000.json").write_text(json.dumps({"add": {"path": "part-00000.parquet"}}) + "\n")

    def log(self):
        return self.root / TABLES[0] / "_delta_log"

    def replace(self, content):
        (self.log() / "00000000000000000000.json").write_text(content)

    def test_valid_parquet(self):
        verify(self.root, "parquet")

    def test_corrupt_second_part(self):
        (self.root / TABLES[0] / "part-00001.parquet").write_bytes(b"PAR1")
        with self.assertRaisesRegex(ValueError, "too short"):
            verify(self.root, "parquet")

    def test_invalid_parquet_footer(self):
        (self.root / TABLES[0] / "part-00000.parquet").write_bytes(b"PAR1x" + struct.pack("<I", 1) + b"NOPE")
        with self.assertRaisesRegex(ValueError, "footer"):
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

    def test_duplicate_action_key(self):
        self.replace('{"add":{},"add":{}}\n')
        with self.assertRaisesRegex(ValueError, "duplicate"):
            verify(self.root, "delta")

    def test_duplicate_nested_key(self):
        self.replace('{"add":{"path":"x","path":"y"}}\n')
        with self.assertRaisesRegex(ValueError, "duplicate"):
            verify(self.root, "delta")

    def test_duplicate_deeply_nested_key(self):
        self.replace('{"add":{"stats":{"a":1,"a":2}}}\n')
        with self.assertRaisesRegex(ValueError, "duplicate"):
            verify(self.root, "delta")

    def test_duplicate_in_second_record(self):
        self.replace('{"protocol":{}}\n{"add":{"x":1,"x":2}}\n')
        with self.assertRaisesRegex(ValueError, "duplicate"):
            verify(self.root, "delta")

    def test_nonstandard_numeric_constant(self):
        self.replace('{"add":{"n":NaN}}\n')
        with self.assertRaisesRegex(ValueError, "nonstandard"):
            verify(self.root, "delta")

    def test_valid_same_nested_key_in_separate_objects(self):
        self.replace('{"add":{"a":{"id":1},"b":{"id":2}}}\n')
        verify(self.root, "delta")


if __name__ == "__main__":
    unittest.main()
