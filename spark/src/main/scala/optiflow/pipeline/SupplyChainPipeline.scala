package optiflow.pipeline

import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._

/** Batch normalization and warehouse/store/route feasibility checks.
  * Run independently from the lightweight OR-Tools CLI; the normalized
  * Parquet/Delta tables form a reproducible analytics layer.
  */
object SupplyChainPipeline {
  private val warehousesSchema = StructType(Seq(
    StructField("warehouse_id", StringType, nullable = true),
    StructField("inventory", IntegerType, nullable = true),
    StructField("outbound_capacity", IntegerType, nullable = true)
  ))
  private val storesSchema = StructType(Seq(
    StructField("store_id", StringType, nullable = true),
    StructField("demand", IntegerType, nullable = true)
  ))
  private val routesSchema = StructType(Seq(
    StructField("warehouse_id", StringType, nullable = true),
    StructField("store_id", StringType, nullable = true),
    StructField("unit_cost", DoubleType, nullable = true),
    StructField("capacity", IntegerType, nullable = true)
  ))

  def readCsv(spark: SparkSession, path: String, schema: StructType): DataFrame =
    spark.read.option("header", "true").option("mode", "FAILFAST")
      .schema(schema).csv(path)

  private def assertNoRows(df: DataFrame, message: String): Unit =
    require(df.limit(1).count() == 0L, message)

  def normalize(
      warehouses: DataFrame,
      stores: DataFrame,
      routes: DataFrame
  ): (DataFrame, DataFrame, DataFrame, DataFrame) = {
    val w = warehouses.select(trim(col("warehouse_id")).as("warehouse_id"),
      col("inventory"), col("outbound_capacity"))
    val s = stores.select(trim(col("store_id")).as("store_id"), col("demand"))
    val r = routes.select(trim(col("warehouse_id")).as("warehouse_id"),
      trim(col("store_id")).as("store_id"), col("unit_cost"), col("capacity"))

    assertNoRows(w.filter(col("warehouse_id").isNull || length(col("warehouse_id")) === 0 ||
      col("inventory").isNull || col("inventory") < 0 ||
      col("outbound_capacity").isNull || col("outbound_capacity") < 0), "Invalid warehouse")
    assertNoRows(s.filter(col("store_id").isNull || length(col("store_id")) === 0 ||
      col("demand").isNull || col("demand") < 0), "Invalid store")
    assertNoRows(r.filter(col("warehouse_id").isNull || length(col("warehouse_id")) === 0 ||
      col("store_id").isNull || length(col("store_id")) === 0 ||
      col("unit_cost").isNull || isnan(col("unit_cost")) ||
      col("unit_cost") < 0 || col("unit_cost") === lit(Double.PositiveInfinity) ||
      col("capacity").isNull || col("capacity") < 0), "Invalid route")
    assertNoRows(w.groupBy("warehouse_id").count().filter(col("count") > 1), "Duplicate warehouse")
    assertNoRows(s.groupBy("store_id").count().filter(col("count") > 1), "Duplicate store")
    assertNoRows(r.groupBy("warehouse_id", "store_id").count().filter(col("count") > 1), "Duplicate route")
    assertNoRows(r.join(w.select("warehouse_id"), Seq("warehouse_id"), "left_anti"),
      "Route references missing warehouse")
    assertNoRows(r.join(s.select("store_id"), Seq("store_id"), "left_anti"),
      "Route references missing store")

    val opportunities = r.join(w, Seq("warehouse_id"))
      .join(s, Seq("store_id"))
      .withColumn("warehouse_available", least(col("inventory"), col("outbound_capacity")))
      .withColumn("route_feasible_units", least(col("capacity"), col("warehouse_available"), col("demand")))
      .withColumn("max_route_transport_cost", col("route_feasible_units") * col("unit_cost"))
      .select("warehouse_id", "store_id", "unit_cost", "capacity",
        "warehouse_available", "demand", "route_feasible_units", "max_route_transport_cost")
    (w, s, r, opportunities)
  }

  def main(args: Array[String]): Unit = {
    require(args.length == 2 || args.length == 3,
      "Usage: SupplyChainPipeline <input-directory> <output-directory> [parquet|delta]")
    val format = if (args.length == 3) args(2).toLowerCase else "parquet"
    require(Set("parquet", "delta").contains(format), "Format must be parquet or delta")
    val builder = SparkSession.builder().appName("OptiFlow supply-chain normalization")
      .master(sys.props.getOrElse("spark.master", "local[*]"))
      .config("spark.ui.enabled", "false")
    if (format == "delta") {
      builder.config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    }
    val spark = builder.getOrCreate()
    try {
      val input = args(0).stripSuffix("/")
      val output = args(1).stripSuffix("/")
      val (w, s, r, opportunities) = normalize(
        readCsv(spark, s"$input/warehouses.csv", warehousesSchema),
        readCsv(spark, s"$input/stores.csv", storesSchema),
        readCsv(spark, s"$input/routes.csv", routesSchema)
      )
      Seq("warehouses" -> w, "stores" -> s, "routes" -> r,
        "route_opportunities" -> opportunities).foreach { case (name, frame) =>
        frame.write.mode("overwrite").format(format).save(s"$output/$name")
      }
      println(s"Wrote validated $format datasets to $output")
    } finally spark.stop()
  }
}
