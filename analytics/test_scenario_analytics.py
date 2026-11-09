"""Regression tests for DuckDB scenario impact reporting."""
import json
import tempfile
import unittest
from pathlib import Path

from scenario_analytics import analyze, load_snapshots


def snapshot(cost, fulfilled, shortage):
    return {"schemaVersion": 1, "summary": {
        "optimizedCost": cost, "fulfilledUnits": fulfilled,
        "unfulfilledUnits": shortage, "totalDemand": fulfilled + shortage
    }}


class ScenarioAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write("baseline.json", snapshot(100, 10, 0))
        self.write("closure.json", snapshot(180, 8, 2))
        self.write("savings.json", snapshot(75, 10, 0))
        self.write("manifest.json", {"baseline": "baseline.json", "scenarios": [
            {"id": "closure", "label": "Warehouse closure", "report": "closure.json"},
            {"id": "savings", "label": "Cheaper route", "report": "savings.json"}
        ]})

    def write(self, filename, value):
        (self.root / filename).write_text(json.dumps(value), encoding="utf-8")

    def test_cost_rankings_and_fulfillment_deltas(self):
        headers, rows = analyze(self.root)
        self.assertIn("fulfillment_pct", headers)
        self.assertEqual([row[0] for row in rows], ["closure", "savings"])
        self.assertEqual(rows[0][3], 80)
        self.assertEqual(rows[0][7], -2)
        self.assertEqual(rows[0][8], 2)
        self.assertEqual(rows[1][3], -25)

    def test_empty_catalog_is_valid(self):
        self.write("manifest.json", {"baseline": "baseline.json", "scenarios": []})
        self.assertEqual(analyze(self.root)[1], [])

    def test_duplicate_ids_are_rejected(self):
        self.write("manifest.json", {"baseline": "baseline.json", "scenarios": [
            {"id": "x", "label": "First", "report": "closure.json"},
            {"id": "x", "label": "Second", "report": "savings.json"}
        ]})
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            load_snapshots(self.root)

    def test_path_traversal_is_rejected(self):
        self.write("manifest.json", {"baseline": "../baseline.json", "scenarios": []})
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            load_snapshots(self.root)

    def test_inconsistent_demand_is_rejected(self):
        self.write("closure.json", {"schemaVersion": 1, "summary": {
            "optimizedCost": 180, "fulfilledUnits": 8, "unfulfilledUnits": 1, "totalDemand": 10
        }})
        with self.assertRaisesRegex(ValueError, "equal demand"):
            load_snapshots(self.root)


if __name__ == "__main__":
    unittest.main()
