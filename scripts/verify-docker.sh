#!/usr/bin/env bash
# Isolated end-to-end dashboard check; requires generated Scala scenario reports.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PORT="${OPTIFLOW_DOCKER_PORT:-15173}"
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || (( 10#$PORT < 1024 || 10#$PORT > 65535 )); then
  echo "Invalid OPTIFLOW_DOCKER_PORT (expected 1024-65535): $PORT" >&2
  exit 2
fi
for command in docker python3; do
  command -v "$command" >/dev/null 2>&1 || { echo "Missing prerequisite: $command" >&2; exit 127; }
done
for report in output/allocation.json output/scenarios/manifest.json output/scenarios/baseline.json; do
  test -s "$report" || { echo "Missing generated report: $report" >&2; exit 2; }
done
TMPDIR_VERIFY="$(mktemp -d)"
PROJECT="optiflow-verify-$$"
COMPOSE_FILE="$TMPDIR_VERIFY/compose.json"
STARTED=0
cleanup() {
  status=$?
  trap - EXIT
  if (( STARTED )); then
    if (( status != 0 )); then
      docker compose -p "$PROJECT" -f "$COMPOSE_FILE" logs --no-color --tail=150 >&2 || true
    fi
    docker compose -p "$PROJECT" -f "$COMPOSE_FILE" down --volumes --remove-orphans >&2 || true
  fi
  rm -rf "$TMPDIR_VERIFY"
  exit "$status"
}
trap cleanup EXIT
# Render first so bind paths stay absolute when temporary config lives elsewhere.
docker compose -f "$ROOT/compose.yaml" config --format json | python3 "$ROOT/scripts/isolate_compose.py" "$PORT" > "$COMPOSE_FILE"
docker compose -p "$PROJECT" -f "$COMPOSE_FILE" config --quiet
STARTED=1
docker compose -p "$PROJECT" -f "$COMPOSE_FILE" up --detach --no-build
python3 "$ROOT/scripts/smoke_dashboard.py" --base-url "http://127.0.0.1:$PORT"
echo "PASS: isolated Docker dashboard and Scenario Lab HTTP checks"
