package optiflow

import optiflow.AllocationOptimizer._

/** Deterministic operational disruptions with a before/after comparison. */
object ScenarioSimulator {
  sealed trait Disruption
  final case class WarehouseShutdown(warehouseId: String) extends Disruption
  final case class DemandSurge(storeId: String, extraUnits: Int) extends Disruption
  final case class RouteCapacityReduction(warehouseId: String, storeId: String, newCapacity: Int) extends Disruption
  final case class InventoryShortage(warehouseId: String, lostUnits: Int) extends Disruption

  final case class Comparison(
      baseline: Result,
      scenario: Result,
      costDelta: Double,
      fulfilledDelta: Int,
      shortageDelta: Int
  )

  def applyDisruption(problem: Problem, disruption: Disruption): Problem = disruption match {
    case WarehouseShutdown(id) =>
      require(problem.warehouses.exists(_.id == id), s"Unknown warehouse: $id")
      problem.copy(warehouses = problem.warehouses.map(w =>
        if (w.id == id) w.copy(inventory = 0, outboundCapacity = 0) else w))
    case DemandSurge(id, extra) =>
      require(extra >= 0, "Demand surge must be nonnegative")
      require(problem.stores.exists(_.id == id), s"Unknown store: $id")
      problem.copy(stores = problem.stores.map(s =>
        if (s.id == id) s.copy(demand = Math.addExact(s.demand, extra)) else s))
    case RouteCapacityReduction(warehouseId, storeId, capacity) =>
      require(capacity >= 0, "Route capacity must be nonnegative")
      require(problem.routes.exists(r => r.warehouseId == warehouseId && r.storeId == storeId),
        "Unknown route")
      problem.copy(routes = problem.routes.map(r =>
        if (r.warehouseId == warehouseId && r.storeId == storeId)
          r.copy(capacity = math.min(r.capacity, capacity))
        else r))
    case InventoryShortage(id, lost) =>
      require(lost >= 0, "Inventory shortage must be nonnegative")
      require(problem.warehouses.exists(_.id == id), s"Unknown warehouse: $id")
      problem.copy(warehouses = problem.warehouses.map(w =>
        if (w.id == id) w.copy(inventory = math.max(0, w.inventory - lost)) else w))
  }

  def compare(problem: Problem, disruption: Disruption): Comparison = {
    val before = solve(problem)
    val after = solve(applyDisruption(problem, disruption))
    Comparison(scenario = after, baseline = before,
      costDelta = after.totalCost - before.totalCost,
      fulfilledDelta = after.totalFulfilled - before.totalFulfilled,
      shortageDelta = after.totalUnfulfilled - before.totalUnfulfilled)
  }
}
