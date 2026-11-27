"""Regression coverage for the local Spark snapshot inventory command."""
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from snapshot_inventory import build_inventory
from verify_outputs import TABLES


class SnapshotInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.part = b"PAR1x" + struct.pack("<I", 1) + b"PAR1"
        for table in TABLES:
            directory = self.root / table
            directory.mkdir()
            (directory / "part-0.parquet").write_bytes(self.part)
            log = directory / "_delta_log"
            log.mkdir()
            (log / "00000000000000000000.json").write_text(
                json.dumps({"add": {"path": "part-0.parquet"}}) + "\n")

    def test_parquet_totals_and_order(self):
        directory = self.root / TABLES[0]
        (directory / "part-1.parquet").write_bytes(self.part)
        result = build_inventory(self.root, "parquet")
        self.assertEqual(result["table_count"], len(TABLES))
        self.assertEqual(result["file_count"], len(TABLES) + 1)
        self.assertEqual(result["bytes"], (len(TABLES) + 1) * len(self.part))
        self.assertEqual([t["table"] for t in result["tables"]], list(TABLES))
        self.assertEqual([f["path"] for f in result["tables"][0]["files"]],
                         ["part-0.parquet", "part-1.parquet"])

    def test_delta_ignores_removed_and_orphan_parts(self):
        directory = self.root / TABLES[0]
        (directory / "part-1.parquet").write_bytes(self.part)
        (directory / "part-orphan.parquet").write_bytes(b"bad")
        (directory / "part-0.parquet").write_bytes(b"bad")
        actions = [{"remove": {"path": "part-0.parquet"}},
                   {"add": {"path": "part-1.parquet"}}]
        (directory / "_delta_log" / "00000000000000000001.json").write_text(
            "".join(json.dumps(a) + "\n" for a in actions))
        result = build_inventory(self.root, "delta")
        self.assertEqual(result["scope"], "active_delta_snapshot")
        self.assertEqual(result["file_count"], len(TABLES))
        self.assertEqual(result["tables"][0]["files"],
                         [{"path": "part-1.parquet", "bytes": len(self.part)}])

    def test_missing_active_part_fails(self):
        (self.root / TABLES[0] / "part-0.parquet").unlink()
        with self.assertRaisesRegex(ValueError, "Missing active"):
            build_inventory(self.root, "delta")

    def test_corrupt_active_part_fails(self):
        (self.root / TABLES[0] / "part-0.parquet").write_bytes(b"bad")
        with self.assertRaisesRegex(ValueError, "too short"):
            build_inventory(self.root, "delta")

    def test_missing_table_fails(self):
        (self.root / TABLES[0]).rename(self.root / "moved")
        with self.assertRaisesRegex(ValueError, "Missing parquet table"):
            build_inventory(self.root, "parquet")

    def test_invalid_format_fails(self):
        with self.assertRaisesRegex(ValueError, "Unsupported format"):
            build_inventory(self.root, "csv")

    def test_cli_json_and_failure_exit(self):
        script = Path(__file__).with_name("snapshot_inventory.py")
        cmd = [sys.executable, str(script), str(self.root), "delta"]
        completed = subprocess.run(cmd, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(completed.stdout), build_inventory(self.root, "delta"))
        (self.root / TABLES[0] / "part-0.parquet").unlink()
        failed = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(failed.returncode, 1)
        self.assertEqual(failed.stdout, "")
        self.assertIn("Snapshot inventory failed", failed.stderr)


if __name__ == "__main__":
    unittest.main()
