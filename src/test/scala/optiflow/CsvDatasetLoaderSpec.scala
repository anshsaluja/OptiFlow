package optiflow

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path}
import org.scalatest.funsuite.AnyFunSuite

class CsvDatasetLoaderSpec extends AnyFunSuite {
  private def dataset(warehouses: String, stores: String, routes: String): Path = {
    val dir = Files.createTempDirectory("optiflow-csv-")
    Files.write(dir.resolve("warehouses.csv"), warehouses.getBytes(StandardCharsets.UTF_8))
    Files.write(dir.resolve("stores.csv"), stores.getBytes(StandardCharsets.UTF_8))
    Files.write(dir.resolve("routes.csv"), routes.getBytes(StandardCharsets.UTF_8))
    dir
  }
  private val warehouses = "warehouse_id,inventory,outbound_capacity\nw1,10,8\n"
  private val stores = "store_id,demand\ns1,5\n"
  private val routes = "warehouse_id,store_id,unit_cost,capacity\nw1,s1,2.5,4\n"

  test("loads a complete valid dataset and preserves capacities") {
    val problem = CsvDatasetLoader.load(dataset(warehouses, stores, routes))
    assert(problem.warehouses.head.outboundCapacity == 8)
    assert(problem.routes.head.capacity == 4)
    assert(problem.routes.head.unitCost == 2.5)
    val result = AllocationOptimizer.solve(problem)
    assert(result.totalFulfilled == 4)
    assert(result.totalUnfulfilled == 1)
  }

  test("rejects unknown route endpoints before solving") {
    intercept[IllegalArgumentException] {
      CsvDatasetLoader.load(dataset(warehouses, stores, routes.replace("w1,s1", "missing,s1")))
    }
  }

  test("rejects malformed or negative quantities with line context") {
    val error = intercept[IllegalArgumentException] {
      CsvDatasetLoader.load(dataset(warehouses.replace("w1,10,8", "w1,-10,8"), stores, routes))
    }
    assert(error.getMessage.contains(":2:"))
  }

  test("rejects duplicate routes") {
    intercept[IllegalArgumentException] {
      CsvDatasetLoader.load(dataset(warehouses, stores, routes + "w1,s1,3,2\n"))
    }
  }

  test("rejects non-finite costs") {
    intercept[IllegalArgumentException] {
      CsvDatasetLoader.load(dataset(warehouses, stores, routes.replace("2.5", "NaN")))
    }
  }
}
