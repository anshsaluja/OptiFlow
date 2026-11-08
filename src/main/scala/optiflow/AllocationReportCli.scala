package optiflow

import java.nio.file.Paths

/** Export one reproducible allocation snapshot for dashboard development.
  * Run: sbt "runMain optiflow.AllocationReportCli datasets/demo output/allocation.json"
  */
object AllocationReportCli {
  def main(args: Array[String]): Unit = {
    require(args.length == 2 || args.length == 3,
      "Usage: AllocationReportCli <dataset-directory> <output-json> [shortage-penalty]")
    val penalty = if (args.length == 3) args(2).toDouble else 1000.0
    val problem = CsvDatasetLoader.load(Paths.get(args(0)), penalty)
    val optimized = AllocationOptimizer.solve(problem)
    val greedy = GreedyBaseline.solve(problem)
    val output = Paths.get(args(1))
    AllocationJsonReport.write(output, problem, optimized, greedy)
    println(s"Exported allocation snapshot to ${output.toAbsolutePath}")
  }
}
