# OptiFlow Airflow orchestration (optional local integration)

The DAG at `dags/optiflow_scenarios.py` runs a **manual**, three-step pipeline:
(1) solve the baseline and disruptions with the Scala OR-Tools CLI,
(2) run the SvelteKit report-contract tests against the actual generated JSON,
and (3) export ranked cost/shortage impact metrics with DuckDB.
Tasks fail on subprocess errors; downstream steps do not run after a failure.
This is an optional orchestration entry point, **not** a deployed Airflow service.

## Prerequisites

Use Airflow 2.8+ with Python supported by that Airflow release, Java 17,
sbt, Node 20, and Python DuckDB (`python3 -m pip install 'duckdb>=1.1,<2'`).
Install dashboard dependencies first with `cd dashboard && npm install`.
The Airflow worker must see the same checkout and toolchain as the scheduler.

Set `OPTIFLOW_REPO_ROOT` to the **absolute** path of the repository and
point Airflow's DAG folder to `<repo>/airflow/dags` (or copy the DAG into
your existing DAG folder). For example, in a local Airflow environment:

```bash
export OPTIFLOW_REPO_ROOT="$(pwd)"
export AIRFLOW__CORE__DAGS_FOLDER="$OPTIFLOW_REPO_ROOT/airflow/dags"
airflow dags list
airflow dags test optiflow_local_scenario_pipeline 2026-11-08
```

The DAG is deliberately `schedule=None`: trigger it explicitly when desired.
It writes `output/scenarios/` and `output/scenario-impact.csv` in the
checkout. Do not run multiple copies against the same output directory.
The task timeout is 20 minutes for Scala and analytics, 10 minutes for
frontend validation; each task retries once. Generated outputs are local
artifacts, not committed data.

The optimizer and dashboard do **not** depend on Airflow to run. For a simpler
development workflow use the direct commands in `dashboard/README.md` and
`analytics/README.md`. Airflow execution has not been verified until the
DAG is actually loaded and run in an Airflow environment.
