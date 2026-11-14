"""Regression checks for the Airflow pipeline's dependency order and task wiring.

Run: python3 -m unittest discover -s airflow -p 'test_*.py'
This uses lightweight Airflow stand-ins, not a live scheduler.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_dag_contract import FakeOperator, load_dag


class DependencyOrderTests(unittest.TestCase):
    def test_pipeline_is_strictly_sequential(self):
        edges = []
        original_shift = FakeOperator.__rshift__

        def record_shift(self, downstream):
            edges.append((self.task_id, downstream.task_id))
            return original_shift(self, downstream)

        with tempfile.TemporaryDirectory() as temp:
            with patch.object(FakeOperator, "__rshift__", record_shift):
                module = load_dag(Path(temp))

        self.assertEqual(
            edges,
            [
                ("generate_snapshots", "validate_dashboard_contract"),
                ("validate_dashboard_contract", "export_duckdb_analytics"),
            ],
        )
        self.assertEqual(
            {module.generate.task_id, module.validate.task_id, module.analyze.task_id},
            {"generate_snapshots", "validate_dashboard_contract", "export_duckdb_analytics"},
        )
        self.assertIs(module.generate.python_callable, module.generate_snapshots)
        self.assertIs(module.validate.python_callable, module.check_dashboard_contract)
        self.assertIs(module.analyze.python_callable, module.export_analytics)
        self.assertIsNone(module.dag.options["schedule"])
        self.assertEqual(module.dag.options["max_active_runs"], 1)


if __name__ == "__main__":
    unittest.main()
