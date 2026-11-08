package optiflow.pipeline

import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions._
import org.scalatest.BeforeAndAfterAll
import org.scalatest.funsuite.AnyFunSuite

class SupplyChainPipelineSpec extends AnyFunSuite with BeforeAndAfterAll {
  private var spark: SparkSession = _

  override protected def beforeAll(): Unit = {
    super.beforeAll()
    spark = SparkSession.builder().master("local[2]").appName("OptiFlow Spark tests")
      .config("spark.ui.enabled", "false").getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
  }
  override protected def afterAll(): Unit = {
    if (spark != null) spark.stop()
    super.afterAll()
  }

  private def warehouses = spark.sql(
    "SELECT 'w1' warehouse_id, 10 inventory, 6 outbound_capacity")
  private def stores = spark.sql("SELECT 's1' store_id, 8 demand")
  private def routes = spark.sql(
    "SELECT 'w1' warehouse_id, 's1' store_id, 2.5D unit_cost, 5 capacity")

  test("normalized route opportunity respects every independent bound") {
    val (_, _, _, opportunities) =
      SupplyChainPipeline.normalize(warehouses, stores, routes)
    val row = opportunities.select("warehouse_available", "route_feasible_units",
      "max_route_transport_cost").head()
    assert(row.getInt(0) == 6)
    assert(row.getInt(1) == 5)
    assert(row.getDouble(2) == 12.5)
  }

  test("rejects unknown warehouse references") {
    val bad = routes.withColumn("warehouse_id", lit("missing"))
    intercept[IllegalArgumentException] {
      SupplyChainPipeline.normalize(warehouses, stores, bad)
    }
  }

  test("rejects duplicate routes") {
    intercept[IllegalArgumentException] {
      SupplyChainPipeline.normalize(warehouses, stores, routes.union(routes))
    }
  }

  test("rejects negative demand") {
    val bad = stores.withColumn("demand", lit(-1))
    intercept[IllegalArgumentException] {
      SupplyChainPipeline.normalize(warehouses, bad, routes)
    }
  }
}
