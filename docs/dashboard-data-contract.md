# Allocation dashboard data contract

The Scala optimizer can produce a stable JSON snapshot for a local dashboard.
The report is **not** a live API and should not be described as one.

Run the exporter with the existing demo data:

```bash
sbt "runMain optiflow.AllocationReportCli datasets/demo output/allocation.json"
```

The resulting UTF-8 JSON includes `schemaVersion: 1`, solver status,
the shortage penalty, a cost/fulfillment summary, warehouse capacity,
store demand and shortages, and nonzero shipments. The baseline comparison
uses the same problem and shortage penalty. All arrays are sorted by IDs for
repeatable snapshots. Consumers should reject unknown schema versions.

`savingsVsGreedy` is an absolute cost difference (greedy minus optimized),
not a percentage. Costs are in the dataset's arbitrary consistent monetary
units; no currency is implied. Shipment `transportCost` is units times
route unit cost. Shortage penalties are an explicit modeling assumption,
not observed financial losses.

This export enables a SvelteKit frontend to render a static local scenario
without coupling the browser to the native OR-Tools solver. Interactive
scenario execution and API integration remain future work.
