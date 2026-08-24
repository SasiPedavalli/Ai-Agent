"""Optional PySpark implementation for Databricks/Spark environments.

This module is deliberately separate from the lightweight local demo so the agent can be
run without installing Spark. In Databricks, call `run_pyspark_profile(spark, path)` and
feed the returned metrics into the same governance/policy layer.
"""

from __future__ import annotations


def run_pyspark_profile(spark, path: str):
    from pyspark.sql import functions as F

    df = spark.read.option("header", True).option("inferSchema", True).csv(path)
    row_count = df.count()
    metrics = {"row_count": row_count, "columns": df.columns, "null_counts": {}}
    for col_name in df.columns:
        null_count = df.filter(F.col(col_name).isNull()).count()
        metrics["null_counts"][col_name] = null_count
    return metrics
