"""
PySpark Analytics & Continuous Improvement ETL Job
Translation Quality Analytics & Continuous Improvement Platform

Ingests baseline Parquet and live PostgreSQL operational data, computes distributed
statistical aggregations (p95 latency, quality score, feedback rates), flags anomalies,
and populates the PostgreSQL analytics marts for Grafana dashboards.
"""

import json
import logging
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

# Guarantee Python worker process resolution on Windows
os.environ.setdefault("PYSPARK_PYTHON", "python")
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", "python")

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import config
from sqlalchemy import create_engine, text
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pyspark_etl_job")

INTERIM_DIR = BASE_DIR / "data" / "interim" / "enriched_baseline"


def get_spark_session(app_name: str = "TranslationQualityETL") -> SparkSession:
    """Builds an optimized local SparkSession."""
    return (
        SparkSession.builder.appName(app_name)
        .master("local[1]")
        .config("spark.driver.memory", "1g")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )


def load_baseline_parquet(spark: SparkSession) -> Tuple[DataFrame, DataFrame]:
    """
    Loads baseline Parquet data using PyArrow.
    Separates high-dimensional aggregation metrics from full-text anomalies
    to optimize memory and prevent JVM heap exhaustion on workstation environments.
    """
    import pyarrow.dataset as ds
    logger.info(f"Loading baseline Parquet files from {INTERIM_DIR}...")
    dataset = ds.dataset(str(INTERIM_DIR), format="parquet")
    
    # Read only metric columns for aggregation (avoids shipping megabytes of text across JVM socket)
    metric_cols = [
        "provider", "source_language", "target_language", "style_option",
        "translation_time_ms", "quality_score", "is_anomaly", "created_at"
    ]
    metrics_schema = StructType([
        StructField("provider", StringType(), False),
        StructField("source_language", StringType(), False),
        StructField("target_language", StringType(), False),
        StructField("style_option", StringType(), False),
        StructField("translation_time_ms", IntegerType(), False),
        StructField("quality_score", DoubleType(), False),
        StructField("is_anomaly", BooleanType(), False),
        StructField("created_at", TimestampType(), False),
        StructField("feedback_rating", StringType(), True),
    ])

    tbl_metrics = dataset.to_table(columns=metric_cols)
    pdf_metrics = tbl_metrics.to_pandas()
    pdf_metrics["created_at"] = pd.to_datetime(pdf_metrics["created_at"])
    pdf_metrics["feedback_rating"] = ""
    pdf_metrics["translation_time_ms"] = pdf_metrics["translation_time_ms"].astype(int)
    pdf_metrics["quality_score"] = pdf_metrics["quality_score"].astype(float)
    pdf_metrics["is_anomaly"] = pdf_metrics["is_anomaly"].astype(bool)

    df_metrics = spark.createDataFrame(pdf_metrics, schema=metrics_schema)

    # Read anomaly subset directly with diagnostic text (only flagged rows)
    filter_expr = ds.field("is_anomaly") == True
    tbl_anomalies = dataset.to_table(filter=filter_expr)
    pdf_anomalies = tbl_anomalies.to_pandas().head(200)

    anomaly_schema = StructType([
        StructField("provider", StringType(), True),
        StructField("source_language", StringType(), True),
        StructField("target_language", StringType(), True),
        StructField("source_text", StringType(), True),
        StructField("translated_text", StringType(), True),
        StructField("style_option", StringType(), True),
        StructField("source_char_len", IntegerType(), True),
        StructField("target_char_len", IntegerType(), True),
        StructField("source_word_count", IntegerType(), True),
        StructField("target_word_count", IntegerType(), True),
        StructField("length_ratio", DoubleType(), True),
        StructField("translation_time_ms", IntegerType(), True),
        StructField("confidence_score", DoubleType(), True),
        StructField("quality_score", DoubleType(), True),
        StructField("is_anomaly", BooleanType(), True),
        StructField("anomaly_type", StringType(), True),
        StructField("created_at", StringType(), True),
    ])
    df_anomalies = spark.createDataFrame(pdf_anomalies, schema=anomaly_schema)
    logger.info(f"Loaded {len(pdf_metrics):,} baseline rows for aggregation, {len(pdf_anomalies):,} anomaly candidates.")
    return df_metrics, df_anomalies


def load_live_database_records(spark: SparkSession) -> DataFrame:
    """
    Extracts live translation and feedback records from PostgreSQL via SQLAlchemy/PySpark.
    """
    engine = create_engine(config.database_url)
    query = """
    SELECT
        t.provider,
        t.source_language,
        t.target_language,
        t.source_text,
        o.translated_text,
        o.style_option,
        t.translation_time_ms,
        o.confidence_score,
        f.rating as feedback_rating,
        f.reason as feedback_reason,
        f.comments as feedback_comments,
        t.created_at,
        t.id::text as translation_id,
        o.id::text as option_id
    FROM translations t
    JOIN translation_options o ON t.id = o.translation_id
    LEFT JOIN feedback f ON o.id = f.option_id
    """
    try:
        import pandas as pd
        with engine.connect() as conn:
            pdf = pd.read_sql_query(text(query), conn)

        if pdf.empty:
            logger.info("No live PostgreSQL records found; generating empty DataFrame matching schema.")
            schema = StructType([
                StructField("provider", StringType(), False),
                StructField("source_language", StringType(), False),
                StructField("target_language", StringType(), False),
                StructField("source_text", StringType(), False),
                StructField("translated_text", StringType(), False),
                StructField("style_option", StringType(), False),
                StructField("translation_time_ms", IntegerType(), False),
                StructField("confidence_score", DoubleType(), True),
                StructField("feedback_rating", StringType(), True),
                StructField("feedback_reason", StringType(), True),
                StructField("feedback_comments", StringType(), True),
                StructField("created_at", TimestampType(), True),
                StructField("translation_id", StringType(), True),
                StructField("option_id", StringType(), True),
            ])
            return spark.createDataFrame([], schema)

        logger.info(f"Loaded {len(pdf):,} live translation option records from PostgreSQL.")
        return spark.createDataFrame(pdf)
    except Exception as exc:
        logger.warning(f"Could not load live DB records: {exc}")
        return spark.createDataFrame([], StructType([]))


def compute_daily_metrics(unified_df: DataFrame) -> DataFrame:
    """
    Computes multi-dimensional aggregated reporting data mart across:
    (metric_date, provider, source_language, target_language, style_option).
    """
    logger.info("Computing multi-dimensional quality and latency aggregations...")
    return (
        unified_df.groupBy(
            F.to_date(F.col("created_at")).alias("metric_date"),
            F.col("provider"),
            F.col("source_language"),
            F.col("target_language"),
            F.col("style_option"),
        )
        .agg(
            F.count("*").alias("total_requests"),
            F.round(F.avg("translation_time_ms"), 2).alias("avg_latency_ms"),
            F.round(F.expr("percentile_approx(translation_time_ms, 0.95)"), 2).alias("p95_latency_ms"),
            F.round(F.avg("quality_score"), 2).alias("avg_quality_score"),
            F.sum(F.when(F.col("feedback_rating") == "GOOD", 1).otherwise(0)).alias("good_feedback_count"),
            F.sum(F.when(F.col("feedback_rating") == "POOR", 1).otherwise(0)).alias("poor_feedback_count"),
        )
        .withColumn(
            "poor_feedback_rate",
            F.round(
                F.col("poor_feedback_count")
                / F.when(
                    (F.col("good_feedback_count") + F.col("poor_feedback_count")) > 0,
                    (F.col("good_feedback_count") + F.col("poor_feedback_count")),
                ).otherwise(None),
                4,
            ),
        )
        .fillna({"poor_feedback_rate": 0.0})
    )


def extract_anomalies(unified_df: DataFrame) -> DataFrame:
    """
    Identifies translation anomalies (truncation, runaway repetition, or poor feedback).
    """
    logger.info("Extracting quality and latency anomalies...")
    filter_cond = (F.col("is_anomaly") == True) | (F.col("translation_time_ms") > 5000)
    if "feedback_rating" in unified_df.columns:
        filter_cond = filter_cond | (F.col("feedback_rating") == "POOR")

    return (
        unified_df.filter(filter_cond)
        .select(
            F.col("translation_id") if "translation_id" in unified_df.columns else F.lit(None).alias("translation_id"),
            F.col("option_id") if "option_id" in unified_df.columns else F.lit(None).alias("option_id"),
            F.coalesce(F.col("anomaly_type"), F.lit("POOR_FEEDBACK_DEFECT")).alias("anomaly_type"),
            F.round(F.coalesce(F.lit(1.0) - (F.col("quality_score") / 100.0), F.lit(0.75)), 4).alias("anomaly_score"),
            F.concat(
                F.lit('{"source": "'),
                F.substring(F.col("source_text"), 1, 60),
                F.lit('", "ratio": '),
                F.round(F.col("length_ratio"), 3),
                F.lit('}'),
            ).alias("diagnostic_details"),
            F.current_timestamp().alias("detected_at"),
        )
        .limit(500)
    )


def write_to_postgres(metrics_df: DataFrame, anomalies_df: DataFrame):
    """
    Persists computed aggregates into analytics_daily_metrics and analytics_anomalies tables.
    """
    engine = create_engine(config.database_url)
    metrics_records = [row.asDict() for row in metrics_df.collect()]
    anomalies_records = [row.asDict() for row in anomalies_df.collect()]

    logger.info(f"Persisting {len(metrics_records):,} daily metric slices into PostgreSQL...")
    with engine.begin() as conn:
        # Upsert daily metrics
        for m in metrics_records:
            conn.execute(
                text("""
                INSERT INTO analytics_daily_metrics (
                    metric_date, provider, source_language, target_language, style_option,
                    total_requests, avg_latency_ms, p95_latency_ms, avg_quality_score,
                    good_feedback_count, poor_feedback_count, poor_feedback_rate, computed_at
                ) VALUES (
                    :metric_date, :provider, :source_language, :target_language, :style_option,
                    :total_requests, :avg_latency_ms, :p95_latency_ms, :avg_quality_score,
                    :good_feedback_count, :poor_feedback_count, :poor_feedback_rate, CURRENT_TIMESTAMP
                )
                ON CONFLICT (metric_date, provider, source_language, target_language, style_option)
                DO UPDATE SET
                    total_requests = EXCLUDED.total_requests,
                    avg_latency_ms = EXCLUDED.avg_latency_ms,
                    p95_latency_ms = EXCLUDED.p95_latency_ms,
                    avg_quality_score = EXCLUDED.avg_quality_score,
                    good_feedback_count = EXCLUDED.good_feedback_count,
                    poor_feedback_count = EXCLUDED.poor_feedback_count,
                    poor_feedback_rate = EXCLUDED.poor_feedback_rate,
                    computed_at = CURRENT_TIMESTAMP
                """),
                m,
            )

        logger.info(f"Persisting {len(anomalies_records):,} flagged anomaly records into PostgreSQL...")
        for a in anomalies_records:
            conn.execute(
                text("""
                INSERT INTO analytics_anomalies (
                    anomaly_type, anomaly_score, diagnostic_details, detected_at
                ) VALUES (
                    :anomaly_type, :anomaly_score, :diagnostic_details, :detected_at
                )
                """),
                a,
            )

    logger.info("Database egress completed successfully.")


def run_etl_pipeline():
    """Main pipeline orchestrator."""
    spark = get_spark_session()
    try:
        # 1. Load baseline Parquet (metrics projection + anomaly sample)
        baseline_df, baseline_anomalies_df = load_baseline_parquet(spark)

        # 2. Load live PostgreSQL records
        live_df = load_live_database_records(spark)

        # 3. Unify aggregation datasets
        if not live_df.isEmpty():
            live_metrics = live_df.select(
                "provider", "source_language", "target_language", "style_option",
                "translation_time_ms", F.lit(88.0).alias("quality_score"),
                F.when(F.col("feedback_rating") == "POOR", True).otherwise(False).alias("is_anomaly"),
                "created_at", "feedback_rating"
            )
            unified_metrics_df = baseline_df.unionByName(live_metrics)
        else:
            unified_metrics_df = baseline_df

        # 4. Aggregations & Anomaly Extraction
        metrics_df = compute_daily_metrics(unified_metrics_df)
        anomalies_df = extract_anomalies(baseline_anomalies_df)

        # 5. Egress to PostgreSQL
        write_to_postgres(metrics_df, anomalies_df)
        logger.info("ETL batch job executed successfully.")

    finally:
        spark.stop()


if __name__ == "__main__":
    run_etl_pipeline()
