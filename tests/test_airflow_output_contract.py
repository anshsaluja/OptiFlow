"""Regression tests for the real Airflow smoke harness output contract.

No Airflow installation is needed: mock only the execution boundary, while
letting the production verifier parse actual temporary output artifacts.
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify-airflow-runtime.py"
spec = importlib.util.spec_from_file_location("verify_airflow_runtime", SCRIPT)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class OutputContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / "manifest.json"
        self.analytics = self.root / "scenario-impact.csv"

    def write_valid(self):
        self.manifest.write_text(json.dumps({"scenarios": [{"id": "baseline"}]}))
        self.analytics.write_text("scenario_id,cost\nbaseline,42\n")

    def verify(self, generate=None):
        # The mocked DAG runner is the only producer of artifacts. All output
        # parsing and validation is performed by the real production script.
        if generate is None:
            generate = self.write_valid
        def fake_run(args, env):
            if args[:3] == ["airflow", "dags", "test"]:
                generate()
        with patch.object(verifier, "MANIFEST", self.manifest), \
             patch.object(verifier, "ANALYTICS", self.analytics), \
             patch.object(verifier, "run", side_effect=fake_run), \
             patch.object(verifier, "check_import_errors"), \
             patch.object(verifier.shutil, "which", return_value="/bin/mock"), \
             patch.object(verifier, "REPO", self.root), \
             patch.dict("sys.modules", {"airflow": __import__("types"), "duckdb": __import__("types")}):
            (self.root / "dashboard" / "node_modules").mkdir(parents=True, exist_ok=True)
            return verifier.main()

    def test_valid_artifacts(self):
        self.assertEqual(self.verify(), 0)

    def test_missing_artifacts(self):
        self.assertEqual(self.verify(generate=lambda: None), 1)

    def test_unchanged_artifacts(self):
        self.write_valid()
        self.assertEqual(self.verify(generate=lambda: None), 1)

    def test_malformed_json(self):
        def produce():
            self.write_valid()
            self.manifest.write_text("{invalid")
        self.assertEqual(self.verify(produce), 1)

    def test_empty_scenarios(self):
        def produce():
            self.write_valid()
            self.manifest.write_text('{"scenarios": []}')
        self.assertEqual(self.verify(produce), 1)

    def test_header_only_csv(self):
        def produce():
            self.write_valid()
            self.analytics.write_text("scenario_id,cost\n")
        self.assertEqual(self.verify(produce), 1)

    def test_duplicate_csv_headers(self):
        def produce():
            self.write_valid()
            self.analytics.write_text("cost,cost\n1,2\n")
        self.assertEqual(self.verify(produce), 1)

    def test_inconsistent_csv_columns(self):
        def produce():
            self.write_valid()
            self.analytics.write_text("scenario_id,cost\nbaseline,42,extra\n")
        self.assertEqual(self.verify(produce), 1)


if __name__ == "__main__":
    unittest.main()
