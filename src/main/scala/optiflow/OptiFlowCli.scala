package optiflow

import java.nio.file.Paths
import optiflow.AllocationOptimizer._

/** Run with: sbt "run datasets/demo" */
object OptiFlowCli {
  def main(args: Array[String]): Unit = {
    require(args.length <= 2, "Usage: sbt \"run [dataset-directory] [shortage-penalty]\"")
    val directory = Paths.get(args.headOption.getOrElse("datasets/demo"))
    val penalty = if (args.length == 2) args(1).toDouble else 1000.0
    val problem = CsvDatasetLoader.load(directory, penalty)
    val optimized = AllocationOptimizer.solve(problem)
    val greedy = GreedyBaseline.solve(problem)
    println(s"Warehouses: ${problem.warehouses.size}, stores: ${problem.stores.size}, routes: ${problem.routes.size}")
    println(f"Optimized cost: ${optimized.totalCost}%.2f (transport ${optimized.transportationCost}%.2f, shortage ${optimized.shortageCost}%.2f)")
    println(f"Greedy cost: ${greedy.totalCost}%.2f")
    println(s"Fulfilled: ${optimized.totalFulfilled}, unfulfilled: ${optimized.totalUnfulfilled}")
    optimized.shipments.sortBy(s => (s.warehouseId, s.storeId)).foreach { s =>
      println(s"${s.warehouseId} -> ${s.storeId}: ${s.units} units")
    }
    if (greedy.totalCost > 0)
      println(f"Cost improvement vs greedy: ${100.0 * (greedy.totalCost - optimized.totalCost) / greedy.totalCost}%.2f%%")
  }
}
