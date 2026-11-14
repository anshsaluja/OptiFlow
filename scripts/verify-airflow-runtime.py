#!/usr/bin/env python3
"""Verify the OptiFlow DAG with a real, installed Apache Airflow runtime.

Run from any directory after installing Airflow, Java 17, sbt, Node 20,
dashboard dependencies and DuckDB. This intentionally does not mock Airflow.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DAG_ID = "optiflow_local_scenario_pipeline"
REPO = Path(__file__).resolve().parents[1]
DAG_FOLDER = REPO / "airflow" / "dags"
MANIFEST = REPO / "output" / "scenarios" / "manifest.json"
ANALYTICS = REPO / "output" / "scenario-impact.csv"


def run(args: list[str], env: dict[str, str]) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=REPO, env=env, check=True, timeout=2400)


def main() -> int:
    missing = [tool for tool in ("airflow", "java", "sbt", "node", "npm")
               if shutil.which(tool) is None]
    if missing:
        print(f"Missing required executables: {', '.join(missing)}", file=sys.stderr)
        return 2
    try:
        import airflow  # noqa: F401
        import duckdb  # noqa: F401
    except ImportError as exc:
        print(f"Missing Python runtime dependency: {exc}", file=sys.stderr)
        return 2

    if not (REPO / "dashboard" / "node_modules").is_dir():
        print("Install dashboard dependencies: cd dashboard && npm install",
              file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="optiflow-airflow-") as home:
        env = {**os.environ,
               "AIRFLOW_HOME": home,
               "AIRFLOW__CORE__DAGS_FOLDER": str(DAG_FOLDER),
               "AIRFLOW__CORE__LOAD_EXAMPLES": "False",
               "OPTIFLOW_REPO_ROOT": str(REPO)}
        try:
            # A fresh metadata database avoids relying on a preexisting scheduler.
            run(["airflow", "db", "migrate"], env)
            run(["airflow", "dags", "list-import-errors", "--output", "json"], env)
            run(["airflow", "dags", "test", DAG_ID, "2026-11-14"], env)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            print(f"Real Airflow execution failed: {exc}", file=sys.stderr)
            return 1

    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        assert manifest["scenarios"], "No disruption scenarios produced"
        assert ANALYTICS.is_file() and ANALYTICS.stat().st_size > 0, (
            "Analytics CSV missing or empty"
        )
    except (OSError, ValueError, KeyError, AssertionError) as exc:
        print(f"Output verification failed: {exc}", file=sys.stderr)
        return 1
    print(f"Real Airflow DAG succeeded: {len(manifest['scenarios'])} scenarios; "
          f"analytics at {ANALYTICS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
