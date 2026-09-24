# PySpark ETL & Quality Analytics Pipeline
# Translation Quality Analytics & Continuous Improvement Platform

**Status**: Pipeline Architecture Specification (Updated for Multi-Provider Dimensions)  
**Version**: 1.1.0  
**Phase**: Architecture & Documentation

---

## 1. Pipeline Overview & Execution Architecture
The PySpark ETL subsystem serves as the core big data processing engine for the platform. It executes batch transformations across historical baseline datasets (staged OPUS-100 Parquet files) and live operational records extracted from PostgreSQL.

### Execution Blueprint:
```
[ Staged Baseline Parquet ]   [ PostgreSQL JDBC Source ]
(OPUS-100 68,000 pairs)      (Live HF / Cohere / Mock records)
            \                         /
             v                       v
        +---------------------------------+
        |  1. Unified Ingestion Stage     |
        +---------------------------------+
                        |
                        v
        +---------------------------------+
        |  2. Validation & Cleansing      |
        +---------------------------------+
                        |
                        v
        +---------------------------------+
        |  3. Feature Engineering         |
        +---------------------------------+
                        |
                        v
        +---------------------------------+
        |  4. Quality & Anomaly Engine    |
        +---------------------------------+
                        |
                        v
        +---------------------------------+
        |  5. Multi-Dimensional Aggreg.   |
        |  (Date, Pair, Style, Provider)  |
        +---------------------------------+
                        |
                        v
        +---------------------------------+
        |  6. Database Egress (JDBC)      |
        +---------------------------------+
                        |
                        v
        [ PostgreSQL Analytics Tables ]
```

---

## 2. Granular Pipeline Stages

### Stage 1: Ingestion
- Ingests staged baseline Parquet files from `data/interim/enriched_baseline/` using `spark.read.parquet()`.
- Ingests live application records via PostgreSQL JDBC:
  - `translations` joined with `translation_options` and left-joined with `feedback`.
- Normalizes the `provider` column (defaults to `'opus100_baseline'` for historical data; `'huggingface'`, `'cohere'`, or `'mock'` for live records).
- Unifies schemas and casts timestamps.

### Stage 2: Validation & Cleansing
- **Null Filtering**: Discards records where `source_text` or `translated_text` is null (`filter(col("source_text").isNotNull() & col("translated_text").isNotNull())`).
- **Whitespace Stripping**: Applies `trim()` on all text fields; removes records where text length equals 0.
- **Language Code Sanitization**: Normalizes language tags to lower-case ISO 639-1 (`lower(trim(col("target_language")))`).
- **Deduplication**: Deduplicates records on composite key `(source_language, target_language, md5(lower(source_text)))`.

### Stage 3: Feature Engineering
All structural and textual metrics are computed natively using distributed Spark SQL functions rather than precomputed upfront:
- **Character Lengths**:
  - `source_char_len = length(col("source_text"))`
  - `target_char_len = length(col("translated_text"))`
- **Word Counts**:
  - `source_word_count = size(split(trim(col("source_text")), "\\s+"))`
  - `target_word_count = size(split(trim(col("translated_text")), "\\s+"))`
- **Length Ratio**:
  - `length_ratio = col("target_char_len") / col("source_char_len")`
- **Latency Binning**:
  - `latency_bucket = when(col("translation_time_ms") < 1000, "FAST")`
    `.when(col("translation_time_ms") <= 3000, "NORMAL")`
    `.otherwise("SLOW")`

### Stage 4: Quality & Anomaly Engine
Computes an auditable, deterministic Quality Score ($Q$) out of 100:
$$Q = w_c \cdot C + w_l \cdot S_l + w_f \cdot S_f$$
Where:
- $C$ = Normalized Confidence Score ($0 \le C \le 100$, default 85 if unmeasured).
- $S_l$ = Length Consistency Score (penalizes extreme expansion/contraction outside expected language-pair bounds).
- $S_f$ = Feedback Factor (100 for `GOOD`, 20 for `POOR`, 85 for unrated baseline).
- Weights: $w_c = 0.35, w_l = 0.35, w_f = 0.30$.

**Anomaly Flags**:
- Flagged if `length_ratio < 0.25` (Severe Truncation) or `length_ratio > 4.0` (Runaway Hallucination/Repetition).
- Flagged if `translation_time_ms > 8000` (Extreme Latency Spike).
- Flagged if `feedback_rating == 'POOR'`.

### Stage 5: Dimensional Aggregation
Aggregates metrics along multi-dimensional grouping sets:
- **Group Keys**: `metric_date` (derived via `to_date(col("created_at"))`), `provider`, `source_language`, `target_language`, `style_option`.
- **Aggregated Metrics**:
  - `total_requests = count("*")`
  - `avg_latency_ms = avg("translation_time_ms")`
  - `p95_latency_ms = expr("percentile_approx(translation_time_ms, 0.95)")`
  - `avg_quality_score = avg("quality_score")`
  - `good_feedback_count = sum(when(col("feedback_rating") == "GOOD", 1).otherwise(0))`
  - `poor_feedback_count = sum(when(col("feedback_rating") == "POOR", 1).otherwise(0))`
  - `poor_feedback_rate = poor_feedback_count / nullif(good_feedback_count + poor_feedback_count, 0)`

> **Analytical Note**: The pipeline records performance metrics across providers (e.g., average latency by provider, volume by provider). However, the platform avoids making sweeping claims of one provider being objectively "better" without statistically significant, controlled human evaluation benchmarks.

### Stage 6: Egress (PostgreSQL)
- Writes summary metrics into `analytics_daily_metrics` using Spark JDBC.
- Writes flagged anomaly rows into `analytics_anomalies`.

---

## 3. Spark Session & Workstation Resource Profile

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("TranslationQualityETL") \
    .master("local[4]") \
    .config("spark.driver.memory", "4g") \
    .config("spark.sql.shuffle.partitions", "8") \
    .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
    .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
    .getOrCreate()
```
