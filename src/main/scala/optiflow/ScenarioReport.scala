package optiflow

import optiflow.AllocationOptimizer._
import optiflow.ScenarioSimulator._

/** Compare a reproducible catalog of operational shocks against one solved baseline.
  * Deltas are relative to the same unmodified input, not to preceding shocks.
  */
object ScenarioReport {
  final case class Scenario(name: String, disruption: Disruption)
  final case class Impact(
      name: String,
      costDelta: Double,
      fulfilledDelta: Int,
      shortageDelta: Int,
      resultingCost: Double,
      resultingFulfilled: Int,
      resultingShortage: Int
  )
  final case class Report(baseline: Result, impacts: Vector[Impact])

  def standardScenarios(problem: Problem): Vector[Scenario] = {
    val warehouseShocks = problem.warehouses.toVector.sortBy(_.id).map { w =>
      Scenario(s"Shutdown warehouse ${w.id}", WarehouseShutdown(w.id))
    }
    val demandShocks = problem.stores.toVector.sortBy(_.id).filter(_.demand > 0).map { s =>
      // A deterministic 25% surge, rounded up to at least one unit.
      val extra = math.max(1, math.ceil(s.demand.toDouble * 0.25).toInt)
      Scenario(s"Demand surge at ${s.id} (+$extra)", DemandSurge(s.id, extra))
    }
    val routeShocks = problem.routes.toVector.sortBy(r => (r.warehouseId, r.storeId))
      .filter(_.capacity > 0).map { r =>
        Scenario(s"Close route ${r.warehouseId} -> ${r.storeId}",
          RouteCapacityReduction(r.warehouseId, r.storeId, 0))
      }
    warehouseShocks ++ demandShocks ++ routeShocks
  }

  def analyze(problem: Problem, scenarios: Seq[Scenario]): Report = {
    require(scenarios.map(_.name).distinct.size == scenarios.size, "Duplicate scenario names")
    val baseline = AllocationOptimizer.solve(problem)
    val impacts = scenarios.toVector.map { scenario =>
      val after = AllocationOptimizer.solve(applyDisruption(problem, scenario.disruption))
      Impact(
        scenario.name,
        after.totalCost - baseline.totalCost,
        after.totalFulfilled - baseline.totalFulfilled,
        after.totalUnfulfilled - baseline.totalUnfulfilled,
        after.totalCost,
        after.totalFulfilled,
        after.totalUnfulfilled
      )
    }
    Report(baseline, impacts.sortBy(i => (-i.costDelta, i.name)))
  }

  def toCsv(report: Report): String = {
    def escape(s: String): String = "\"" + s.replace("\"", "\"\"") + "\""
    val header = "scenario,cost_delta,fulfilled_delta,shortage_delta,resulting_cost,resulting_fulfilled,resulting_shortage"
    val rows = report.impacts.map { i =>
      Seq(escape(i.name), i.costDelta.toString, i.fulfilledDelta.toString,
        i.shortageDelta.toString, i.resultingCost.toString,
        i.resultingFulfilled.toString, i.resultingShortage.toString).mkString(",")
    }
    (header +: rows).mkString("\n") + "\n"
  }
}
