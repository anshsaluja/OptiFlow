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
