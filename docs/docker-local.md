# Docker Compose: local dashboard preview

This is a **local read-only snapshot viewer**, not a containerized optimizer, Airflow deployment, or production service. The Scala OR-Tools CLI still runs on the host. The container provides a reproducible Node 20 environment for the SvelteKit UI, and never needs access to Docker secrets or a cloud account.

## Start

Install Java 17 and sbt on the host, then generate both snapshots from the repository root:

```sh
sbt "runMain optiflow.AllocationReportCli datasets/demo output/allocation.json"
sbt "runMain optiflow.ScenarioSnapshotCli datasets/demo output/scenarios"
docker compose up
```

Visit http://localhost:5173 for the allocation dashboard and http://localhost:5173/scenarios for the Scenario Lab. The dashboard reads the host-generated `output/` directory through a read-only bind mount. Restarting the container is **not** required after regenerating snapshots; refresh the browser page.

The first launch installs dashboard npm dependencies in a named volume; it may take a few minutes. The `.svelte-kit` build directory is another writable named volume, while repository source and generated reports remain read-only inside the container. Port 5173 is bound only to localhost, not the public network.

## Validation and cleanup

```sh
docker compose config
docker compose ps
docker compose down
```

To clear cached dependencies and generated SvelteKit files, use `docker compose down -v` (this removes only the Compose-managed named volumes). Run `cd dashboard && npm run check && npm test` on the host for frontend checks. Scala and integration CI are configured in `.github/workflows/scala-ci.yml`. CI now also generates real Scala allocation and scenario snapshots, starts the Docker Compose dashboard on a GitHub-hosted runner, checks HTTP 200 responses with nonempty bodies for `/` and `/scenarios`, captures container logs on failure, and tears down the service and volumes. This is a container startup/route smoke test, not a browser interaction test or full Airflow runtime test.

**Limitations:** This Compose service has no optimizer API and does not generate snapshots automatically. It is a development preview, not a production deployment. A Docker startup smoke test is configured in CI; check the workflow result before treating container startup as verified.
