package optiflow

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path, Paths}
import optiflow.AllocationOptimizer._
import optiflow.ScenarioReport.standardScenarios
import optiflow.ScenarioSimulator.applyDisruption

/** Produce independently optimized, validated-by-contract JSON snapshots for Scenario Lab.
  * sbt "runMain optiflow.ScenarioSnapshotCli datasets/demo output/scenarios"
  */
object ScenarioSnapshotCli {
  private def quoted(value: String): String = {
    val escaped = value.flatMap {
      case '"' => "\\\""
      case '\\' => "\\\\"
      case '\n' => "\\n"
      case '\r' => "\\r"
      case '\t' => "\\t"
      case c if c < ' ' => f"\\u${c.toInt}%04x"
      case c => c.toString
    }
    "\"" + escaped + "\""
  }

  def export(problem: Problem, output: Path): Unit = {
    Files.createDirectories(output)
    def snapshot(filename: String, current: Problem): Unit =
      AllocationJsonReport.write(output.resolve(filename), current,
        AllocationOptimizer.solve(current), GreedyBaseline.solve(current))

    snapshot("baseline.json", problem)
    // Limit snapshot count to the dashboard's documented manifest bound.
    val scenarios = standardScenarios(problem).take(30).zipWithIndex.map { case (scenario, index) =>
      val id = f"scenario-${index + 1}%02d"
      val filename = id + ".json"
      snapshot(filename, applyDisruption(problem, scenario.disruption))
      s"""    {"id":${quoted(id)},"label":${quoted(scenario.name)},"report":${quoted(filename)}}"""
    }
    val manifest = "{\n  \"baseline\": \"baseline.json\",\n  \"scenarios\": [\n" +
      scenarios.mkString(",\n") + "\n  ]\n}\n"
    Files.write(output.resolve("manifest.json"), manifest.getBytes(StandardCharsets.UTF_8))
  }

  def main(args: Array[String]): Unit = {
    require(args.length == 2 || args.length == 3,
      "Usage: ScenarioSnapshotCli <dataset-directory> <output-directory> [shortage-penalty]")
    val penalty = if (args.length == 3) args(2).toDouble else 1000.0
    val problem = CsvDatasetLoader.load(Paths.get(args(0)), penalty)
    export(problem, Paths.get(args(1)))
    println(s"Generated scenario snapshots in ${Paths.get(args(1)).toAbsolutePath}")
  }
}
