# DuckDB scenario impact analytics

This small analytics layer queries **real independently optimized Scala scenario snapshots**; it does not fabricate metrics or require a running database service.

Generate snapshots from the repository root:

```bash
sbt "runMain optiflow.ScenarioSnapshotCli datasets/demo output/scenarios"
python3 -m pip install 'duckdb>=1.1,<2'
python3 -m unittest discover -s analytics -p 'test_*.py' -v
python3 analytics/scenario_analytics.py output/scenarios output/scenario-impact.csv
```

The CSV ranks scenarios by increased total optimized cost (highest risk first), with a deterministic ID tie-break. Columns include optimized cost, cost delta versus the **same unmodified baseline**, fulfilled and unfulfilled units, fulfillment percentage, and fulfillment/shortage deltas. Negative cost delta means savings. Zero-demand scenarios return an empty fulfillment percentage rather than dividing by zero.

The script checks manifest IDs, snapshot paths, JSON schema version, finite nonnegative metrics, and demand accounting before inserting into an in-memory DuckDB table. It refuses path traversal and symlinks that escape the snapshot directory. The existing dashboard parser remains the authoritative full shipment-capacity validator; this analytics script deliberately performs only the checks required for aggregate comparisons.

The Scala CI workflow runs the unit tests and then executes the query against freshly generated optimizer snapshots.
