#!/usr/bin/env python3
"""Analyze independently solved OptiFlow snapshots with DuckDB.

Usage: python3 analytics/scenario_analytics.py output/scenarios [output/scenario-impact.csv]
Install: python3 -m pip install duckdb
"""
import csv
import json
import math
import sys
from pathlib import Path

import duckdb


def load_snapshots(directory: Path):
    directory = directory.resolve()
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    scenarios = manifest["scenarios"]
    if not isinstance(scenarios, list) or not 1 <= len(scenarios) <= 30:
        raise ValueError("Scenario manifest must contain between 1 and 30 entries")

    def report(filename):
        if not isinstance(filename, str) or not filename.endswith(".json") or Path(filename).name != filename:
            raise ValueError("Unsafe snapshot filename")
        path = (directory / filename).resolve()
        if path.parent != directory or not path.is_file():
            raise ValueError("Snapshot must be a JSON file within the scenario directory")
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schemaVersion") != 1:
            raise ValueError("Unsupported optimizer report version")
        summary = data["summary"]
        values = tuple(summary[k] for k in ("optimizedCost", "fulfilledUnits", "unfulfilledUnits", "totalDemand"))
        if any(isinstance(v, bool) for v in values[1:]):
            raise ValueError("Report quantities must be safe nonnegative integers")
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v < 0 for v in values):
            raise ValueError("Invalid report metrics")
        if any(not isinstance(v, int) or isinstance(v, bool) or v > (2**53 - 1) for v in values[1:3]):
            raise ValueError("Report quantities must be safe nonnegative integers")
        if values[1] + values[2] > (2**53 - 1):
            raise ValueError("Aggregate fulfillment exceeds safe integer range")
        if not isinstance(values[3], int) or isinstance(values[3], bool) or values[3] > (2**53 - 1):
            raise ValueError("Report quantities must be safe nonnegative integers")
        if values[1] + values[2] != values[3]:
            raise ValueError("Fulfillment and shortage must equal demand")
        return values

    baseline = report(manifest["baseline"])
    seen = set()
    seen_reports = {manifest["baseline"]}
    rows = []
    for entry in scenarios:
        scenario_id, label = entry["id"], entry["label"]
        if not isinstance(scenario_id, str) or not scenario_id.strip():
            raise ValueError("Duplicate or empty scenario ID")
        scenario_id = scenario_id.strip()
        if scenario_id in seen:
            raise ValueError("Duplicate or empty scenario ID")
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Empty scenario label")
        seen.add(scenario_id)
        label = label.strip()
        filename = entry["report"]
        if filename in seen_reports:
            raise ValueError("Duplicate snapshot report reference")
        seen_reports.add(filename)
        rows.append((scenario_id, label, *report(filename)))
    return baseline, rows


def analyze(directory: Path):
    baseline, rows = load_snapshots(directory)
    db = duckdb.connect(":memory:")
    try:
        db.execute("""CREATE TABLE scenarios (
            id VARCHAR, label VARCHAR, cost DOUBLE,
            fulfilled BIGINT, shortage BIGINT, demand BIGINT
        )""")
        if rows:
            db.executemany("INSERT INTO scenarios VALUES (?, ?, ?, ?, ?, ?)", rows)
        result = db.execute("""
            SELECT id, label,
                   round(cost, 2) AS optimized_cost,
                   round(cost - ?, 2) AS cost_delta,
                   fulfilled, shortage, demand,
                   round(100.0 * fulfilled / NULLIF(demand, 0), 2) AS fulfillment_pct,
                   fulfilled - ? AS fulfilled_delta,
                   shortage - ? AS shortage_delta
            FROM scenarios
            ORDER BY cost_delta DESC, id ASC
        """, [baseline[0], baseline[1], baseline[2]])
        return [c[0] for c in result.description], result.fetchall()
    finally:
        db.close()


def main(argv):
    if len(argv) not in (2, 3):
        raise SystemExit("Usage: scenario_analytics.py <snapshot-directory> [output-csv]")
    headers, rows = analyze(Path(argv[1]))
    if len(argv) == 3:
        output = Path(argv[2])
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(rows)
        print(f"Wrote {len(rows)} scenario comparisons to {output}")
    else:
        writer = csv.writer(sys.stdout)
        writer.writerow(headers)
        writer.writerows(rows)


if __name__ == "__main__":
    main(sys.argv)
