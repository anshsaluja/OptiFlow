package optiflow

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path}
import optiflow.AllocationOptimizer._

/** Deterministic, dependency-free JSON contract for dashboard consumers.
  * Numbers are emitted as JSON numbers and identifiers are escaped correctly.
  */
object AllocationJsonReport {
  private def quoted(value: String): String = {
    val escaped = value.flatMap {
      case '"' => "\\\""
      case '\\' => "\\\\"
      case '\b' => "\\b"
      case '\f' => "\\f"
      case '\n' => "\\n"
      case '\r' => "\\r"
      case '\t' => "\\t"
      case c if c < ' ' => f"\\u${c.toInt}%04x"
      case c => c.toString
    }
    "\"" + escaped + "\""
  }
  private def numeric(value: Double): String = {
    require(java.lang.Double.isFinite(value), "Cannot serialize non-finite JSON number")
    java.lang.Double.toString(value)
  }
  def render(problem: Problem, optimized: Result, greedy: Result): String = {
    val warehouses = problem.warehouses.sortBy(_.id).map { w =>
      s"""{"id":${quoted(w.id)},"inventory":${w.inventory},"outboundCapacity":${w.outboundCapacity}}"""
    }.mkString(",")
    val stores = problem.stores.sortBy(_.id).map { s =>
      s"""{"id":${quoted(s.id)},"demand":${s.demand},"unmet":${optimized.unmetByStore.getOrElse(s.id, 0)}}"""
    }.mkString(",")
    val shipments = optimized.shipments.sortBy(s => (s.warehouseId, s.storeId)).map { s =>
      s"""{"warehouseId":${quoted(s.warehouseId)},"storeId":${quoted(s.storeId)},"units":${s.units},"unitCost":${numeric(s.unitCost)},"transportCost":${numeric(s.units * s.unitCost)}}"""
    }.mkString(",")
    val improvement = greedy.totalCost - optimized.totalCost
    s"""{
       |  "schemaVersion": 1,
       |  "status": ${quoted(optimized.status)},
       |  "shortagePenalty": ${numeric(problem.shortagePenalty)},
       |  "summary": {
       |    "totalDemand": ${problem.stores.map(_.demand.toLong).sum},
       |    "fulfilledUnits": ${optimized.totalFulfilled},
       |    "unfulfilledUnits": ${optimized.totalUnfulfilled},
       |    "optimizedCost": ${numeric(optimized.totalCost)},
       |    "transportationCost": ${numeric(optimized.transportationCost)},
       |    "shortageCost": ${numeric(optimized.shortageCost)},
       |    "greedyCost": ${numeric(greedy.totalCost)},
       |    "savingsVsGreedy": ${numeric(improvement)}
       |  },
       |  "warehouses": [$warehouses],
       |  "stores": [$stores],
       |  "shipments": [$shipments]
       |}""".stripMargin
  }

  def write(path: Path, problem: Problem, optimized: Result, greedy: Result): Unit = {
    val parent = path.toAbsolutePath.getParent
    if (parent != null) Files.createDirectories(parent)
    Files.write(path, (render(problem, optimized, greedy) + "\n").getBytes(StandardCharsets.UTF_8))
  }
}
