# OptiFlow Spark analytics pipeline

This is an independent Scala 2.12 / Spark 3.5.3 subproject, isolated from the lightweight OR-Tools optimizer. It ingests operational CSV files, validates IDs and numeric fields, joins routes with warehouse capacity and store demand, and writes four analytics tables: warehouses, stores, routes, and route_opportunities.

## Run locally

Requires Java 17 and sbt. From the repository root:

```bash
cd spark
sbt 'run ../datasets/demo ../datasets/processed parquet'
# Optional Delta Lake output:
sbt 'run ../datasets/demo ../datasets/processed-delta delta'
```

Spark output paths are directories, not individual files. Do not commit generated output. This pipeline computes **per-route upper bounds**, not a globally feasible allocation: multiple routes share warehouse inventory and store demand. The OR-Tools engine remains responsible for globally consistent shipments. The Spark pipeline is intentionally not yet wired into the root sbt CI; run it separately until its integration tests and Java 17 runtime are verified.
