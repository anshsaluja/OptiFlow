package optiflow

import org.scalatest.funsuite.AnyFunSuite
import optiflow.AllocationOptimizer._

class AllocationJsonReportSpec extends AnyFunSuite {
  private val problem = Problem(
    Seq(Warehouse("north\\\"east", 5, 5)),
    Seq(Store("store\\n1", 8)),
    Seq(Route("north\\\"east", "store\\n1", 2.0, 5))
  )

  test("report contains fulfillment, shortages, cost and escaped identifiers") {
    val optimized = AllocationOptimizer.solve(problem)
    val greedy = GreedyBaseline.solve(problem)
    val json = AllocationJsonReport.render(problem, optimized, greedy)
    assert(json.contains("\"schemaVersion\": 1"))
    assert(json.contains("\"fulfilledUnits\": 5"))
    assert(json.contains("\"unfulfilledUnits\": 3"))
    assert(json.contains("\"optimizedCost\": 3010.0"))
    assert(json.contains("north\\\\\\\"east"))
    assert(json.contains("store\\\\n1"))
  }

  test("report order does not depend on warehouse insertion order") {
    val a = Problem(Seq(Warehouse("z", 1, 1), Warehouse("a", 1, 1)), Seq.empty, Seq.empty)
    val b = a.copy(warehouses = a.warehouses.reverse)
    val result = Result("OPTIMAL", Seq.empty, Map.empty, 0.0, 0.0)
    assert(AllocationJsonReport.render(a, result, result) ==
      AllocationJsonReport.render(b, result, result))
  }

  test("write creates parent directory and UTF-8 report") {
    val dir = java.nio.file.Files.createTempDirectory("optiflow-json")
    val path = dir.resolve("nested/report.json")
    try {
      val result = AllocationOptimizer.solve(problem)
      AllocationJsonReport.write(path, problem, result, GreedyBaseline.solve(problem))
      val contents = new String(java.nio.file.Files.readAllBytes(path), java.nio.charset.StandardCharsets.UTF_8)
      assert(contents.contains("\"shipments\""))
      assert(contents.endsWith("\n"))
    } finally {
      java.nio.file.Files.deleteIfExists(path)
      java.nio.file.Files.deleteIfExists(path.getParent)
      java.nio.file.Files.deleteIfExists(dir)
    }
  }
}
