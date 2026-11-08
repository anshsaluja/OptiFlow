package optiflow

import org.scalatest.funsuite.AnyFunSuite
import optiflow.AllocationOptimizer._
import optiflow.ScenarioSimulator._
import optiflow.ScenarioReport._

class ScenarioReportSpec extends AnyFunSuite {
  private val problem = Problem(
    Seq(Warehouse("w1", 10, 10), Warehouse("w2", 10, 10)),
    Seq(Store("s1", 8)),
    Seq(Route("w1", "s1", 1.0, 8), Route("w2", "s1", 4.0, 8))
  )

  test("warehouse shutdown increases transport cost without unmet demand") {
    val report = analyze(problem, Seq(Scenario("shutdown", WarehouseShutdown("w1"))))
    assert(report.baseline.transportationCost == 8.0)
    assert(report.impacts.head.costDelta == 24.0)
    assert(report.impacts.head.shortageDelta == 0)
    assert(report.impacts.head.resultingFulfilled == 8)
  }

  test("scenario results are independently compared against baseline") {
    val scenarios = Seq(
      Scenario("surge", DemandSurge("s1", 5)),
      Scenario("shutdown", WarehouseShutdown("w1"))
    )
    val report = analyze(problem, scenarios)
    assert(report.baseline.totalFulfilled == 8)
    assert(report.impacts.find(_.name == "shutdown").get.resultingFulfilled == 8)
    assert(report.impacts.find(_.name == "surge").get.resultingFulfilled == 13)
  }

  test("standard catalog is deterministic and includes shutdowns, surges, and route closures") {
    val scenarios = standardScenarios(problem)
    assert(scenarios.size == 5)
    assert(scenarios.map(_.name).distinct.size == scenarios.size)
    assert(scenarios.exists(_.name.contains("Demand surge")))
    assert(scenarios.count(_.name.startsWith("Close route")) == 2)
  }

  test("CSV escapes scenario names and reports signed deltas") {
    val report = analyze(problem, Seq(Scenario("shutdown, \"primary\"", WarehouseShutdown("w1"))))
    val csv = toCsv(report)
    assert(csv.contains("\"shutdown, \"\"primary\"\"\""))
    assert(csv.contains("24.0"))
    assert(csv.split("\\n").length == 2)
  }

  test("duplicate scenario names are rejected") {
    intercept[IllegalArgumentException] {
      analyze(problem, Seq(Scenario("same", WarehouseShutdown("w1")),
        Scenario("same", WarehouseShutdown("w2"))))
    }
  }
}
