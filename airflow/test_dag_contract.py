"""Lightweight DAG contract checks without installing the Airflow scheduler.

These tests validate command wiring and task dependencies with Airflow stand-ins.
They do NOT substitute for loading the DAG in a real Airflow installation.
"""
import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

DAG_FILE = Path(__file__).parent / "dags" / "optiflow_scenarios.py"


class FakeDAG:
    def __init__(self, **kwargs):
        self.options = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeOperator:
    def __init__(self, task_id, python_callable):
        self.task_id = task_id
        self.python_callable = python_callable

    def __rshift__(self, other):
        return other


def load_dag(root):
    airflow = types.ModuleType("airflow")
    airflow.__path__ = []
    airflow.DAG = FakeDAG
    operators = types.ModuleType("airflow.operators")
    operators.__path__ = []
    python = types.ModuleType("airflow.operators.python")
    python.PythonOperator = FakeOperator
    with patch.dict(sys.modules, {
        "airflow": airflow,
        "airflow.operators": operators,
        "airflow.operators.python": python,
    }), patch.dict(os.environ, {"OPTIFLOW_REPO_ROOT": str(root)}):
        spec = importlib.util.spec_from_file_location("optiflow_test_dag", DAG_FILE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


class AirflowWiringTests(unittest.TestCase):
    def test_manual_dag_and_tasks(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_dag(temp)
            self.assertEqual(module.dag.options["schedule"], None)
            self.assertEqual(module.dag.options["max_active_runs"], 1)
            self.assertEqual(module.generate.task_id, "generate_snapshots")
            self.assertEqual(module.validate.task_id, "validate_dashboard_contract")
            self.assertEqual(module.analyze.task_id, "export_duckdb_analytics")

    def test_optimizer_and_analytics_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_dag(temp)
            snapshots = Path(temp) / "output" / "scenarios"
            snapshots.mkdir(parents=True)
            (snapshots / "manifest.json").write_text('{"scenarios": []}')
            with patch.object(module.subprocess, "run") as run:
                module.generate_snapshots()
                self.assertEqual(run.call_args.args[0][0], "sbt")
                self.assertIn("ScenarioSnapshotCli", run.call_args.args[0][1])
                self.assertTrue(run.call_args.kwargs["check"])
                self.assertEqual(run.call_args.kwargs["cwd"], Path(temp))
            output = Path(temp) / "output" / "scenario-impact.csv"
            output.parent.mkdir(parents=True)
            output.write_text("scenario,cost\nbaseline,0\n")
            with patch.object(module.subprocess, "run") as run:
                module.export_analytics()
                self.assertEqual(run.call_args.args[0][1], "analytics/scenario_analytics.py")
                self.assertTrue(run.call_args.kwargs["check"])

    def test_validation_requires_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_dag(temp)
            with self.assertRaises(FileNotFoundError):
                module.check_dashboard_contract()
            snapshots = Path(temp) / "output" / "scenarios"
            snapshots.mkdir(parents=True)
            (snapshots / "manifest.json").write_text("{}")
            with patch.object(module.subprocess, "run") as run:
                module.check_dashboard_contract()
                self.assertEqual(run.call_args.args[0], ["npm", "test"])
                self.assertEqual(run.call_args.kwargs["env"]["OPTIFLOW_SCENARIO_DIR"], str(snapshots))

    def test_generation_rejects_missing_or_empty_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_dag(temp)
            with patch.object(module.subprocess, "run"):
                with self.assertRaisesRegex(RuntimeError, "nonempty scenario manifest"):
                    module.generate_snapshots()
                snapshots = Path(temp) / "output" / "scenarios"
                snapshots.mkdir(parents=True)
                (snapshots / "manifest.json").write_text("")
                with self.assertRaisesRegex(RuntimeError, "nonempty scenario manifest"):
                    module.generate_snapshots()

    def test_analytics_does_not_accept_stale_csv(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_dag(temp)
            output = Path(temp) / "output" / "scenario-impact.csv"
            output.parent.mkdir(parents=True)
            output.write_text("old,stale,data\\n")
            with patch.object(module.subprocess, "run") as run:
                with self.assertRaisesRegex(RuntimeError, "missing or empty"):
                    module.export_analytics()
                run.assert_called_once()
                self.assertFalse(output.exists())

    def test_missing_checkout_fails_before_subprocess(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_dag(Path(temp) / "missing")
            with patch.object(module.subprocess, "run") as run:
                with self.assertRaises(FileNotFoundError):
                    module.generate_snapshots()
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
