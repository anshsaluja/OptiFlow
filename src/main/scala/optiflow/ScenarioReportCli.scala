package optiflow

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Paths}
import optiflow.ScenarioReport._

/** sbt "runMain optiflow.ScenarioReportCli datasets/demo reports/scenarios.csv" */
object ScenarioReportCli {
  def main(args: Array[String]): Unit = {
    require(args.length <= 3,
      "Usage: sbt \"runMain optiflow.ScenarioReportCli [dataset-directory] [output-csv] [shortage-penalty]\"")
    val directory = Paths.get(args.headOption.getOrElse("datasets/demo"))
    val output = Paths.get(args.lift(1).getOrElse("reports/scenarios.csv"))
    val penalty = args.lift(2).map(_.toDouble).getOrElse(1000.0)
    val problem = CsvDatasetLoader.load(directory, penalty)
    val report = analyze(problem, standardScenarios(problem))
    val absolute = output.toAbsolutePath.normalize()
    Option(absolute.getParent).foreach(parent => Files.createDirectories(parent))
    Files.write(absolute, toCsv(report).getBytes(StandardCharsets.UTF_8))
    println(f"Baseline cost: ${report.baseline.totalCost}%.2f")
    println(s"Analyzed ${report.impacts.size} scenarios; report: $absolute")
    report.impacts.take(5).foreach { i =>
      println(f"${i.name}: cost delta ${i.costDelta}%+.2f, shortage delta ${i.shortageDelta}%+d")
    }
  }
}
