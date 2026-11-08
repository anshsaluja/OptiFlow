package optiflow

import optiflow.AllocationOptimizer._

/** Cost and fulfillment comparison against a reproducible greedy heuristic. */
object AllocationComparison {
  final case class Report(
      optimized: Result,
      greedy: Result,
      costSavings: Double,
      fulfillmentGain: Int,
      relativeSavingsPercent: Double
  )

  def compare(problem: Problem): Report = {
    val optimized = AllocationOptimizer.solve(problem)
    val greedy = GreedyBaseline.solve(problem)
    val savings = greedy.totalCost - optimized.totalCost
    val percent = if (greedy.totalCost == 0) 0.0 else savings / greedy.totalCost * 100.0
    Report(optimized, greedy, savings, optimized.totalFulfilled - greedy.totalFulfilled, percent)
  }
}
