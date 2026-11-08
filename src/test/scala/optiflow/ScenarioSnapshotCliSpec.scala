package optiflow

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path}
import org.scalatest.funsuite.AnyFunSuite
import optiflow.AllocationOptimizer._

class ScenarioSnapshotCliSpec extends AnyFunSuite {
  private val problem = Problem(
    Seq(Warehouse("w1", 10, 10), Warehouse("w2", 10, 10)),
    Seq(Store("s1", 8)),
    Seq(Route("w1", "s1", 1.0, 8), Route("w2", "s1", 4.0, 8))
  )

  private def withTempDirectory(test: Path => Unit): Unit = {
    val directory = Files.createTempDirectory("optiflow-scenarios-")
    try test(directory)
    finally {
      val paths = Files.walk(directory)
      try {
        import scala.collection.JavaConverters._
        paths.iterator().asScala.toVector.reverse.foreach(Files.deleteIfExists(_))
      } finally paths.close()
    }
  }

  private def read(path: Path): String =
    new String(Files.readAllBytes(path), StandardCharsets.UTF_8)

  test("exports baseline and each deterministic disruption as separate JSON snapshots") {
    withTempDirectory { directory =>
      ScenarioSnapshotCli.export(problem, directory)
      val manifest = read(directory.resolve("manifest.json"))
      assert(manifest.contains("\"baseline\": \"baseline.json\""))
      assert((1 to 5).forall { index =>
        val filename = f"scenario-$index%02d.json"
        manifest.contains(filename) && Files.isRegularFile(directory.resolve(filename))
      })
      assert(read(directory.resolve("baseline.json")).contains("\"fulfilledUnits\": 8"))
      assert(read(directory.resolve("scenario-01.json")).contains("\"transportationCost\": 32.0"))
      assert(read(directory.resolve("scenario-03.json")).contains("\"totalDemand\": 10"))
    }
  }

  test("repeated exports are byte-for-byte deterministic") {
    withTempDirectory { directory =>
      ScenarioSnapshotCli.export(problem, directory)
      val first = Files.list(directory)
      val before = try {
        import scala.collection.JavaConverters._
        first.iterator().asScala.map(p => p.getFileName.toString -> read(p)).toMap
      } finally first.close()
      ScenarioSnapshotCli.export(problem, directory)
      val second = Files.list(directory)
      val after = try {
        import scala.collection.JavaConverters._
        second.iterator().asScala.map(p => p.getFileName.toString -> read(p)).toMap
      } finally second.close()
      assert(before == after)
    }
  }

  test("empty scenario catalog exports valid empty manifest") {
    withTempDirectory { directory =>
      ScenarioSnapshotCli.export(Problem(Nil, Nil, Nil), directory)
      val manifest = read(directory.resolve("manifest.json"))
      assert(manifest.contains("\"scenarios\": ["))
      assert(manifest.contains("]"))
      assert(Files.isRegularFile(directory.resolve("baseline.json")))
    }
  }
}
