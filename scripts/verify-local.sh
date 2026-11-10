#!/usr/bin/env bash
# Reproducible local integration gate. Run with: bash scripts/verify-local.sh
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

for command in sbt node npm python3; do
  if ! command -v "$command" >/dev/null 2>&1; then
    printf 'Missing prerequisite: %s\n' "$command" >&2
    exit 127
  fi
done

echo '[1/6] Scala optimizer tests'
sbt test
echo '[2/6] Generate allocation report'
sbt "runMain optiflow.AllocationReportCli datasets/demo output/allocation.json"
echo '[3/6] Generate scenario reports'
sbt "runMain optiflow.ScenarioSnapshotCli datasets/demo output/scenarios"
test -s output/allocation.json
test -s output/scenarios/manifest.json

echo '[4/6] Dashboard static checks, tests and production build'
(
  cd dashboard
  npm install --no-package-lock --no-audit --no-fund
  npm run check
  npm test
  npm run build
)

echo '[5/6] Python analytics and orchestration unit tests'
# Keep the DuckDB dependency isolated from the developer's global Python.
# A temporary environment also avoids requiring an activated project venv.
PY_ENV="$(mktemp -d)"
cleanup_python_env() { rm -rf "$PY_ENV"; }
trap cleanup_python_env EXIT
python3 -m venv "$PY_ENV"
"$PY_ENV/bin/python" -m pip install --disable-pip-version-check 'duckdb>=1.1,<2'
"$PY_ENV/bin/python" -m unittest discover -s analytics -p 'test_*.py' -v
"$PY_ENV/bin/python" -m unittest discover -s airflow -p 'test_*.py' -v

echo '[6/6] Export scenario impact CSV with DuckDB'
"$PY_ENV/bin/python" analytics/scenario_analytics.py output/scenarios output/scenario-impact.csv
test -s output/scenario-impact.csv
echo 'PASS: optimizer reports, dashboard, Python checks and analytics export'
echo 'NOTE: Docker Compose startup and Airflow scheduler execution are separate checks.'
