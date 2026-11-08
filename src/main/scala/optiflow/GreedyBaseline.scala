package optiflow

import optiflow.AllocationOptimizer._

/** A deterministic, feasible but non-optimal reference allocation.
  * Stores are processed in input order, choosing cheapest available routes.
  * It respects every constraint and makes no global trade-off between stores.
  */
object GreedyBaseline {
  def solve(problem: Problem): Result = {
    require(problem.shortagePenalty > 0 && java.lang.Double.isFinite(problem.shortagePenalty), "Invalid penalty")
    require(problem.warehouses.map(_.id).distinct.size == problem.warehouses.size, "Duplicate warehouses")
    require(problem.stores.map(_.id).distinct.size == problem.stores.size, "Duplicate stores")
    require(problem.routes.map(r => (r.warehouseId, r.storeId)).distinct.size == problem.routes.size, "Duplicate routes")
    require(problem.warehouses.forall(w => w.inventory >= 0 && w.outboundCapacity >= 0), "Invalid warehouse")
    require(problem.stores.forall(_.demand >= 0), "Invalid demand")
    require(problem.routes.forall(r => r.capacity >= 0 && r.unitCost >= 0 && java.lang.Double.isFinite(r.unitCost)), "Invalid route")
    val warehouses = problem.warehouses.map(w => w.id -> w).toMap
    require(problem.routes.forall(r => warehouses.contains(r.warehouseId) &&
      problem.stores.exists(_.id == r.storeId)), "Unknown route endpoint")

    val remainingWarehouse = scala.collection.mutable.Map(
      problem.warehouses.map(w => w.id -> math.min(w.inventory, w.outboundCapacity)): _*)
    val shipments = scala.collection.mutable.ArrayBuffer.empty[Shipment]
    val shortages = scala.collection.mutable.Map.empty[String, Int]
    problem.stores.foreach { store =>
      var remainingDemand = store.demand
      val candidates = problem.routes.filter(_.storeId == store.id)
        .sortBy(r => (r.unitCost, r.warehouseId))
      candidates.foreach { route =>
        if (remainingDemand > 0 && route.unitCost < problem.shortagePenalty) {
          val units = math.min(remainingDemand, math.min(route.capacity, remainingWarehouse(route.warehouseId)))
          if (units > 0) {
            shipments += Shipment(route.warehouseId, store.id, units, route.unitCost)
            remainingWarehouse(route.warehouseId) -= units
            remainingDemand -= units
          }
        }
      }
      shortages(store.id) = remainingDemand
    }
    Result(
      "GREEDY_BASELINE",
      shipments.toVector,
      shortages.toMap,
      shipments.map(s => s.units * s.unitCost).sum,
      shortages.values.sum * problem.shortagePenalty
    )
  }
}
