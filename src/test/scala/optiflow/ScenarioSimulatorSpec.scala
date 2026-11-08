package optiflow

import org.scalatest.funsuite.AnyFunSuite
import optiflow.AllocationOptimizer._
import optiflow.ScenarioSimulator._

class ScenarioSimulatorSpec extends AnyFunSuite {
  private val problem = Problem(
    Seq(Warehouse("east", 8, 8), Warehouse("west", 8, 8)),
    Seq(Store("central", 10)),
    Seq(Route("east", "central", 1.0, 8), Route("west", "central", 4.0, 8))
  )

  test("warehouse shutdown reroutes stock and reports shortage") {
    val result = compare(problem, WarehouseShutdown("east"))
    assert(result.baseline.totalFulfilled == 10)
    assert(result.scenario.totalFulfilled == 8)
    assert(result.shortageDelta == 2)
    assert(result.scenario.shipments.forall(_.warehouseId == "west"))
  }

  test("demand surge adds unmet demand when capacity is exhausted") {
    val result = compare(problem, DemandSurge("central", 10))
    assert(result.scenario.totalFulfilled == 16)
    assert(result.scenario.totalUnfulfilled == 4)
  }

  test("route capacity reductions cannot increase capacity") {
    val modified = applyDisruption(problem, RouteCapacityReduction("east", "central", 3))
    assert(modified.routes.find(_.warehouseId == "east").get.capacity == 3)
  }

  test("negative disruptions are rejected") {
    intercept[IllegalArgumentException] { applyDisruption(problem, InventoryShortage("east", -1)) }
  }
}
