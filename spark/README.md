# OptiFlow Spark analytics pipeline

This is an independent Scala 2.12 / Spark 3.5.3 subproject, isolated from the lightweight OR-Tools optimizer. It ingests operational CSV files, validates IDs and numeric fields, joins routes with warehouse capacity and store demand, and writes five analytics tables: warehouses, stores, routes, route_opportunities, and network_summary.

## Run locally

Requires Java 17 and sbt. From the repository root:

```bash
cd spark
sbt 'run ../datasets/demo ../datasets/processed parquet'
# Optional Delta Lake output:
sbt 'run ../datasets/demo ../datasets/processed-delta delta'
```

Spark output paths are directories, not individual files. Do not commit generated output. This pipeline computes **per-route upper bounds**, not a globally feasible allocation: multiple routes share warehouse inventory and store demand. The OR-Tools engine remains responsible for globally consistent shipments. The Spark pipeline is intentionally not yet wired into the root sbt CI; run it separately until its integration tests and Java 17 runtime are verified.

## Network-wide diagnostics

The `network_summary` output has one row with warehouse/store/route counts,
raw inventory, inventory capped by outbound throughput, total demand, and the
minimum shortage implied by aggregate supply. This shortage is a **lower bound**:
route bottlenecks and disconnected stores can increase actual shortages.
Never sum `route_feasible_units` across routes to claim global fulfillment;
route upper bounds share supply and demand. Use the OR-Tools optimizer for
actual allocations and costs.
