ThisBuild / scalaVersion := "2.12.18"
ThisBuild / organization := "io.optiflow"

lazy val root = (project in file("."))
  .settings(
    name := "optiflow",
    libraryDependencies ++= Seq(
      "com.google.ortools" % "ortools-java" % "9.11.4210",
      "org.scalatest" %% "scalatest" % "3.2.19" % Test,
      "org.scalameta" %% "munit" % "1.0.2" % Test
    ),
    Test / fork := true,
    run / fork := true
  )
