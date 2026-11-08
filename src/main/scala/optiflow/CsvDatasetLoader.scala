package optiflow

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path}
import scala.collection.JavaConverters._
import scala.util.Try
import optiflow.AllocationOptimizer._

/** Strict, reproducible CSV ingestion for optimizer-ready operational datasets.
  * CSV fields must not contain commas, quotes or embedded newlines.
  * Invalid data fails with a filename and line number instead of being silently dropped.
  */
object CsvDatasetLoader {
  private def records(path: Path, columns: Seq[String]): Vector[(Int, Vector[String])] = {
    require(Files.isRegularFile(path), s"Missing dataset: $path")
    val lines = Files.readAllLines(path, StandardCharsets.UTF_8).asScala.toVector
    require(lines.nonEmpty, s"Empty dataset: $path")
    require(lines.head.stripPrefix("\uFEFF").split(",", -1).map(_.trim).toVector == columns,
      s"Unexpected CSV header in $path; expected ${columns.mkString(",")}")
    lines.zipWithIndex.drop(1).filterNot(_._1.trim.isEmpty).map { case (line, index) =>
      require(!line.contains('"'), s"$path:${index + 1}: quoted CSV is unsupported")
      val values = line.split(",", -1).map(_.trim).toVector
      require(values.size == columns.size && values.forall(_.nonEmpty),
        s"$path:${index + 1}: expected ${columns.size} nonempty columns")
      (index + 1, values)
    }
  }

  private def int(path: Path, line: Int, value: String, name: String): Int =
    Try(value.toInt).toOption.filter(_ >= 0)
      .getOrElse(throw new IllegalArgumentException(s"$path:$line: $name must be a nonnegative integer"))

  private def cost(path: Path, line: Int, value: String): Double =
    Try(value.toDouble).toOption.filter(v => v >= 0 && java.lang.Double.isFinite(v))
      .getOrElse(throw new IllegalArgumentException(s"$path:$line: unit_cost must be finite and nonnegative"))

  def load(directory: Path, shortagePenalty: Double = 1000.0): Problem = {
    val warehousesPath = directory.resolve("warehouses.csv")
    val storesPath = directory.resolve("stores.csv")
    val routesPath = directory.resolve("routes.csv")
    val warehouses = records(warehousesPath, Seq("warehouse_id", "inventory", "outbound_capacity"))
      .map { case (line, c) => Warehouse(c(0), int(warehousesPath, line, c(1), "inventory"),
        int(warehousesPath, line, c(2), "outbound_capacity")) }
    val stores = records(storesPath, Seq("store_id", "demand"))
      .map { case (line, c) => Store(c(0), int(storesPath, line, c(1), "demand")) }
    val routes = records(routesPath, Seq("warehouse_id", "store_id", "unit_cost", "capacity"))
      .map { case (line, c) => Route(c(0), c(1), cost(routesPath, line, c(2)),
        int(routesPath, line, c(3), "capacity")) }
    require(warehouses.nonEmpty && stores.nonEmpty, "Dataset requires warehouses and stores")
    val problem = Problem(warehouses, stores, routes, shortagePenalty)
    // Validate cross-file keys before invoking native solver.
    require(warehouses.map(_.id).distinct.size == warehouses.size, "Duplicate warehouse IDs")
    require(stores.map(_.id).distinct.size == stores.size, "Duplicate store IDs")
    require(routes.map(r => (r.warehouseId, r.storeId)).distinct.size == routes.size, "Duplicate routes")
    require(routes.forall(r => warehouses.exists(_.id == r.warehouseId) &&
      stores.exists(_.id == r.storeId)), "Route references unknown warehouse or store")
    require(shortagePenalty > 0 && java.lang.Double.isFinite(shortagePenalty), "Invalid shortage penalty")
    problem
  }
}
