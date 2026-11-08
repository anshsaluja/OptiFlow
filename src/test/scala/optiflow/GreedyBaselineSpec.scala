package optiflow

import org.scalatest.funsuite.AnyFunSuite
import optiflow.AllocationOptimizer._

class GreedyBaselineSpec extends AnyFunSuite {
  test("greedy honors route and warehouse capacity") {
    val problem = Problem(
      Seq(Warehouse("a", 9, 4)),
      Seq(Store("s1", 5), Store("s2", 5)),
      Seq(Route("a", "s1", 1.0, 3), Route("a", "s2", 1.0, 5)))
    val result = GreedyBaseline.solve(problem)
    assert(result.totalFulfilled == 4)
    assert(result.totalUnfulfilled == 6)
    assert(result.shipments.find(_.storeId == "s1").get.units == 3)
    assert(result.shipments.find(_.storeId == "s2").get.units == 1)
  }

  test("global optimizer beats greedy store-order allocation") {
    val problem = Problem(
      Seq(Warehouse("a", 1, 1), Warehouse("b", 1, 1)),
      Seq(Store("flexible", 1), Store("dependent", 1)),
      Seq(Route("a", "flexible", 1.0, 1),
          Route("b", "flexible", 2.0, 1),
          Route("a", "dependent", 1.0, 1)),
      shortagePenalty = 100.0)
    val report = AllocationComparison.compare(problem)
    assert(report.greedy.totalUnfulfilled == 1)
    assert(report.optimized.totalUnfulfilled == 0)
    assert(report.fulfillmentGain == 1)
    assert(report.costSavings > 0)
  }

  test("greedy avoids uneconomic shipments when penalty is cheaper") {
    val result = GreedyBaseline.solve(Problem(
      Seq(Warehouse("a", 10, 10)),
      Seq(Store("s", 2)),
      Seq(Route("a", "s", 50.0, 10)),
      shortagePenalty = 5.0))
    assert(result.totalFulfilled == 0)
    assert(result.totalUnfulfilled == 2)
    assert(result.totalCost == 10.0)
  }

  test("zero demand produces finite comparison percentage") {
    val report = AllocationComparison.compare(Problem(
      Seq(Warehouse("a", 0, 0)), Seq(Store("s", 0)), Seq.empty))
    assert(report.relativeSavingsPercent == 0.0)
    assert(report.costSavings == 0.0)
  }

  test("invalid route references fail early") {
    intercept[IllegalArgumentException] {
      GreedyBaseline.solve(Problem(Seq.empty, Seq(Store("s", 1)),
        Seq(Route("missing", "s", 1.0, 1))))
    }
  }
}
