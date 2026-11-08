# OptiFlow dashboard

SvelteKit + TypeScript snapshot viewer for the Scala allocation optimizer. This is **not** a live optimizer or a scenario editor.

From the repository root, first generate a report:

```bash
sbt "runMain optiflow.AllocationReportCli datasets/demo output/allocation.json"
```

Then:

```bash
cd dashboard
npm install
npm run check
npm run dev
```

Open the local URL printed by Vite. The server reads `../output/allocation.json` relative to the dashboard working directory. Set `OPTIFLOW_REPORT_PATH` to an absolute path to load another trusted snapshot. Missing or malformed reports display a useful empty state rather than fabricated data. The UI is read-only, with route filtering and sorting.

Cost values are dataset monetary units, not necessarily dollars. Savings compare optimal cost with a greedy baseline; shortage costs represent a modeling penalty. Scenario editing, API execution, and live updates are not implemented yet.


## Generate and inspect disruption scenarios

From the repository root, run:

```bash
sbt "runMain optiflow.ScenarioSnapshotCli datasets/demo output/scenarios"
cd dashboard
npm install
npm run check
npm test
npm run dev
```

Open `/scenarios` in the local dashboard. The Scala CLI solves the baseline and
up to 30 deterministic disruptions **independently**, including warehouse
shutdowns, demand surges, and route closures. It writes
`output/scenarios/manifest.json` and corresponding JSON allocation snapshots.
The dashboard compares those actual optimizer results rather than calculating
a fictional scenario outcome in the browser. Set
`OPTIFLOW_SCENARIOS_PATH` to an absolute manifest path when using a different
output directory. The manifest is read server-side; all referenced snapshots
must be JSON files contained within the manifest directory.

The generated scenario catalog is intentionally capped at 30 entries for a
portfolio-sized local demo. Scenario labels and identifiers are deterministic
for the same input dataset. Running the command again replaces the generated
files; use a fresh output directory when switching datasets to avoid stale
snapshots from a previous run.
