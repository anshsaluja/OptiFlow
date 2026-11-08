ThisBuild / scalaVersion := "2.12.18"
ThisBuild / organization := "io.optiflow"

lazy val sparkPipeline = (project in file(".")).settings(
  name := "optiflow-spark-pipeline",
  libraryDependencies ++= Seq(
    "org.apache.spark" %% "spark-sql" % "3.5.3",
    "io.delta" %% "delta-spark" % "3.2.1",
    "org.scalatest" %% "scalatest" % "3.2.19" % Test
  ),
  Compile / run / fork := true,
  Test / fork := true,
  javaOptions ++= Seq("--add-exports=java.base/sun.nio.ch=ALL-UNNAMED"),
  Test / javaOptions ++= Seq("--add-exports=java.base/sun.nio.ch=ALL-UNNAMED")
)
