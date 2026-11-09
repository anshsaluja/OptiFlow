"""OptiFlow local snapshot pipeline.

Requires Apache Airflow 2.8+ in the scheduler environment, plus Java 17,
sbt, Python and DuckDB on the same worker. Trigger manually after mounting
the repository at OPTIFLOW_REPO_ROOT. No network services are required.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

REPO_ROOT = Path(os.environ.get("OPTIFLOW_REPO_ROOT", "/opt/optiflow")).resolve()
SNAPSHOTS = REPO_ROOT / "output" / "scenarios"
ANALYTICS = REPO_ROOT / "output" / "scenario-impact.csv"


def run_command(*argv: str) -> None:
    """Fail the task on a nonzero exit status; never invoke a shell."""
    if not REPO_ROOT.is_dir():
        raise FileNotFoundError(
            f"OptiFlow checkout missing at {REPO_ROOT}; set OPTIFLOW_REPO_ROOT"
        )
    subprocess.run(argv, cwd=REPO_ROOT, check=True, timeout=1200)


def generate_snapshots() -> None:
    # A previous run must never satisfy the success check for this run.
    manifest = SNAPSHOTS / "manifest.json"
    if manifest.exists():
        manifest.unlink()
    run_command(
        "sbt",
        f"runMain optiflow.ScenarioSnapshotCli datasets/demo {SNAPSHOTS}",
    )
    if not manifest.is_file() or manifest.stat().st_size == 0:
        raise RuntimeError("Optimizer did not produce a nonempty scenario manifest")


def check_dashboard_contract() -> None:
    manifest_path = SNAPSHOTS / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("Scenario manifest missing after generation")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise RuntimeError("Scenario manifest is not valid JSON") from exc
    if not isinstance(manifest, dict) or not isinstance(manifest.get("baseline"), str) or not isinstance(manifest.get("scenarios"), list):
        raise RuntimeError("Scenario manifest is missing baseline or scenarios")
    reports = [manifest["baseline"]]
    for scenario in manifest["scenarios"]:
        if not isinstance(scenario, dict) or not isinstance(scenario.get("report"), str):
            raise RuntimeError("Scenario manifest contains an invalid scenario report")
        reports.append(scenario["report"])
    for name in reports:
        if not name.endswith(".json") or Path(name).name != name or not (SNAPSHOTS / name).is_file():
            raise RuntimeError(f"Scenario report missing or unsafe: {name}")
    subprocess.run(
        ["npm", "test"],
        cwd=REPO_ROOT / "dashboard",
        env={**os.environ, "OPTIFLOW_SCENARIO_DIR": str(SNAPSHOTS)},
        check=True,
        timeout=600,
    )


def export_analytics() -> None:
    # Never accept a CSV left by an earlier successful DAG run.
    if ANALYTICS.exists():
        ANALYTICS.unlink()
    run_command(
        "python3",
        "analytics/scenario_analytics.py",
        str(SNAPSHOTS),
        str(ANALYTICS),
    )
    if not ANALYTICS.is_file() or ANALYTICS.stat().st_size == 0:
        raise RuntimeError("Analytics output is missing or empty")


with DAG(
    dag_id="optiflow_local_scenario_pipeline",
    description="Generate, validate and analyze actual optimizer scenario snapshots",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=2)},
    tags=["optiflow", "local"],
) as dag:
    generate = PythonOperator(task_id="generate_snapshots", python_callable=generate_snapshots)
    validate = PythonOperator(task_id="validate_dashboard_contract", python_callable=check_dashboard_contract)
    analyze = PythonOperator(task_id="export_duckdb_analytics", python_callable=export_analytics)
    generate >> validate >> analyze
