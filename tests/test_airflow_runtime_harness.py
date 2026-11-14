"""Offline regression tests for the real-Airflow smoke harness.

These tests do not substitute for running Apache Airflow; they verify that the
harness rejects malformed import diagnostics and detects changed artifacts.
"""
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify-airflow-runtime.py"
spec = importlib.util.spec_from_file_location("optiflow_airflow_smoke", SCRIPT)
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class AirflowSmokeHarnessTests(unittest.TestCase):
    def test_missing_artifact_has_no_signature(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(smoke.signature(Path(directory) / "missing.csv"))

    def test_modified_artifact_changes_signature(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.csv"
            path.write_text("a")
            original = smoke.signature(path)
            path.write_text("a,longer,report")
            self.assertNotEqual(original, smoke.signature(path))

    def test_import_errors_are_rejected_even_on_successful_exit(self):
        result = subprocess.CompletedProcess([], 0, stdout=json.dumps(
            [{"filepath": "broken.py", "stack_trace": "bad import"}]), stderr="")
        with patch.object(smoke.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "import errors"):
                smoke.check_import_errors({})

    def test_empty_import_error_list_is_accepted(self):
        result = subprocess.CompletedProcess([], 0, stdout="[]", stderr="")
        with patch.object(smoke.subprocess, "run", return_value=result):
            smoke.check_import_errors({})

    def test_invalid_import_error_json_is_rejected(self):
        result = subprocess.CompletedProcess([], 0, stdout="not json", stderr="")
        with patch.object(smoke.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "valid import-error JSON"):
                smoke.check_import_errors({})

    def test_unexpected_import_error_payload_is_rejected(self):
        result = subprocess.CompletedProcess([], 0, stdout="{}", stderr="")
        with patch.object(smoke.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "Unexpected Airflow"):
                smoke.check_import_errors({})


if __name__ == "__main__":
    unittest.main()
