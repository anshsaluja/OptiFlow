package optiflow

import org.scalatest.funsuite.AnyFunSuite
import optiflow.AllocationOptimizer._

class AllocationOptimizerSpec extends AnyFunSuite {
  test("cheapest feasible route wins") {
    val result = solve(Problem(
      Seq(Warehouse("a", 10, 10), Warehouse("b", 10, 10)),
      Seq(Store("store", 8)),
      Seq(Route("a", "store", 2.0, 8), Route("b", "store", 7.0, 8))
    ))
    assert(result.totalFulfilled == 8)
    assert(result.totalUnfulfilled == 0)
    assert(result.transportationCost == 16.0)
    assert(result.shipments.forall(_.warehouseId == "a"))
  }

  test("shortage represents inventory and throughput limits") {
    val result = solve(Problem(
      Seq(Warehouse("a", 10, 3)),
      Seq(Store("store", 8)),
      Seq(Route("a", "store", 2.0, 10))
    ))
    assert(result.totalFulfilled == 3)
    assert(result.totalUnfulfilled == 5)
  }

  test("route capacity is a hard constraint") {
    val result = solve(Problem(
      Seq(Warehouse("a", 10, 10)),
      Seq(Store("store", 8)),
      Seq(Route("a", "store", 1.0, 2))
    ))
    assert(result.totalFulfilled == 2)
    assert(result.totalUnfulfilled == 6)
  }

  test("invalid references are rejected") {
    intercept[IllegalArgumentException] {
      solve(Problem(Seq.empty, Seq(Store("store", 1)), Seq(Route("missing", "store", 1.0, 1))))
    }
  }
}
