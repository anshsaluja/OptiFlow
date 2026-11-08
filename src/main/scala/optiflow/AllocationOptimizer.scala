package optiflow

import com.google.ortools.Loader
import com.google.ortools.linearsolver.{MPConstraint, MPObjective, MPSolver, MPVariable}

/** Integer units are allocated from each warehouse to each store.
  * The objective trades transportation expense against unmet demand,
  * while honoring inventory, route, and warehouse throughput limits.
  */
object AllocationOptimizer {
  final case class Warehouse(id: String, inventory: Int, outboundCapacity: Int)
  final case class Store(id: String, demand: Int)
  final case class Route(warehouseId: String, storeId: String, unitCost: Double, capacity: Int)
  final case class Problem(
      warehouses: Seq[Warehouse],
      stores: Seq[Store],
      routes: Seq[Route],
      shortagePenalty: Double = 1000.0
  )
  final case class Shipment(warehouseId: String, storeId: String, units: Int, unitCost: Double)
  final case class Result(
      status: String,
      shipments: Seq[Shipment],
      unmetByStore: Map[String, Int],
      transportationCost: Double,
      shortageCost: Double
  ) {
    def totalCost: Double = transportationCost + shortageCost
    def totalFulfilled: Int = shipments.map(_.units).sum
    def totalUnfulfilled: Int = unmetByStore.values.sum
  }

  def solve(problem: Problem): Result = {
    require(problem.shortagePenalty > 0 && java.lang.Double.isFinite(problem.shortagePenalty), "Penalty must be finite and positive")
    require(problem.warehouses.map(_.id).distinct.size == problem.warehouses.size, "Duplicate warehouse ID")
    require(problem.stores.map(_.id).distinct.size == problem.stores.size, "Duplicate store ID")
    require(problem.warehouses.forall(w => w.inventory >= 0 && w.outboundCapacity >= 0), "Invalid warehouse quantities")
    require(problem.stores.forall(_.demand >= 0), "Invalid store demand")
    require(problem.routes.forall(r => r.capacity >= 0 && r.unitCost >= 0 && java.lang.Double.isFinite(r.unitCost)), "Invalid route")
    require(problem.routes.map(r => (r.warehouseId, r.storeId)).distinct.size == problem.routes.size, "Duplicate route")
    val warehouses = problem.warehouses.map(w => w.id -> w).toMap
    val stores = problem.stores.map(s => s.id -> s).toMap
    require(problem.routes.forall(r => warehouses.contains(r.warehouseId) && stores.contains(r.storeId)), "Route references unknown node")

    Loader.loadNativeLibraries()
    val solver = MPSolver.createSolver("SCIP")
    require(solver != null, "SCIP solver unavailable")
    try {
      val routeVariables: Seq[(Route, MPVariable)] = problem.routes.map { r =>
        (r, solver.makeIntVar(0.0, r.capacity.toDouble, s"ship_${r.warehouseId}_${r.storeId}"))
      }
      val unmet = problem.stores.map { s =>
        s.id -> solver.makeIntVar(0.0, s.demand.toDouble, s"shortage_${s.id}")
      }.toMap
      problem.warehouses.foreach { w =>
        val cap = math.min(w.inventory, w.outboundCapacity).toDouble
        val constraint = solver.makeConstraint(0.0, cap, s"outbound_${w.id}")
        routeVariables.filter(_._1.warehouseId == w.id).foreach { case (_, variable) =>
          constraint.setCoefficient(variable, 1.0)
        }
      }
      problem.stores.foreach { s =>
        val constraint = solver.makeConstraint(s.demand.toDouble, s.demand.toDouble, s"demand_${s.id}")
        routeVariables.filter(_._1.storeId == s.id).foreach { case (_, variable) =>
          constraint.setCoefficient(variable, 1.0)
        }
        constraint.setCoefficient(unmet(s.id), 1.0)
      }
      val objective = solver.objective()
      routeVariables.foreach { case (route, variable) => objective.setCoefficient(variable, route.unitCost) }
      unmet.values.foreach(objective.setCoefficient(_, problem.shortagePenalty))
      objective.setMinimization()
      val status = solver.solve()
      require(status == MPSolver.ResultStatus.OPTIMAL || status == MPSolver.ResultStatus.FEASIBLE,
        s"No usable optimizer solution: $status")
      val shipments = routeVariables.collect {
        case (route, variable) if variable.solutionValue() >= 0.5 =>
          Shipment(route.warehouseId, route.storeId, math.round(variable.solutionValue()).toInt, route.unitCost)
      }
      val shortages = unmet.map { case (storeId, variable) =>
        storeId -> math.round(variable.solutionValue()).toInt
      }
      Result(
        status.toString,
        shipments,
        shortages,
        shipments.map(s => s.units * s.unitCost).sum,
        shortages.values.sum * problem.shortagePenalty
      )
    } finally solver.delete()
  }
}
