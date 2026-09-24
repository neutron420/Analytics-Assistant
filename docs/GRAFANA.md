# Grafana Analytics & Observability Dashboard
# Translation Quality Analytics & Continuous Improvement Platform

**Status**: Monitoring Specification (Updated for Multi-Provider Architecture)  
**Version**: 1.1.0  
**Phase**: Architecture & Documentation

---

## 1. Overview & Observability Architecture
Grafana provides the operational visibility layer for the platform. It connects directly to PostgreSQL via the native PostgreSQL Data Source to query the pre-aggregated `analytics_daily_metrics` and `analytics_anomalies` tables produced by PySpark.

> **PURPOSE NOTE:**  
> Grafana is strictly for operational intelligence, quality tracking, and pipeline monitoring. It is NOT the end-user translation interface.

---

## 2. Dashboard Layout & Panel Specifications

```
+---------------------------------------------------------------------------------------------------+
|  TRANSLATION QUALITY & OPERATIONAL OBSERVABILITY DASHBOARD                                        |
|  [ Time Range: Last 7 Days v ]   [ Refresh: 1m v ]   [ Target Language: ALL v ] [ Provider: ALL v ]|
+---------------------------------------------------------------------------------------------------+
|  PANEL 1: Total Translations     | PANEL 2: Avg Response Latency    | PANEL 3: Overall Downvote % |
|  [ 68,210 requests ]             | [ 1,240 ms ]                     | [ 4.8% ]                    |
+---------------------------------------------------------------------------------------------------+
|  PANEL 4: Translation Volume Over Time (Time Series by Language Pair)                             |
|  [ Stacked Bar / Area Chart by Target Language: hi, es, fr, de, bn, ja ]                          |
+---------------------------------------------------------------------------------------------------+
|  PANEL 5: Top 5 Language Pairs (Pie/Donut)  | PANEL 6: Avg Latency by Pair (Bar Gauge)            |
|  [ en-es: 22%, en-hi: 22%, en-fr: 20%... ]  | [ en-ja: 1,820ms, en-hi: 1,410ms, en-fr: 980ms... ] |
+---------------------------------------------------------------------------------------------------+
|  PANEL 7: Quality Score Distribution (Histogram)  | PANEL 8: Feedback Defect Distribution (Bar)   |
|  [ Excellent: 62%, Good: 28%, Review: 8%, Poor: 2% ] | [ Too Literal: 42%, Grammar: 28%, Meaning... ] |
+---------------------------------------------------------------------------------------------------+
|  PANEL 9 (Secondary): Provider Volume Mix   | PANEL 10 (Secondary): Avg Latency by Provider       |
|  [ huggingface: 75%, mock: 25%, cohere: 0% ]| [ huggingface: 1,210ms, mock: 3ms, cohere: - ]      |
+---------------------------------------------------------------------------------------------------+
|  PANEL 11: Recent Flagged Quality Anomalies (Interactive Triage Table)                            |
|  [ ID | Pair | Provider | Latency | Length Ratio | Defect Reason | Action Link ]                 |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. SQL Query Catalog for Dashboard Panels

### Core Panel 1: Total Translation Volume (Stat Card)
```sql
SELECT 
  sum(total_requests) AS "Total Translations"
FROM analytics_daily_metrics
WHERE metric_date >= $__timeFrom()::date AND metric_date <= $__timeTo()::date;
```

### Core Panel 2: Average Translation Latency (Stat Card)
```sql
SELECT 
  round(avg(avg_latency_ms)::numeric, 0) AS "Avg Latency (ms)"
FROM analytics_daily_metrics
WHERE metric_date >= $__timeFrom()::date AND metric_date <= $__timeTo()::date;
```

### Core Panel 3: Global Downvote Rate % (Stat Card)
```sql
SELECT 
  round((sum(poor_feedback_count)::numeric / nullif(sum(good_feedback_count + poor_feedback_count), 0) * 100)::numeric, 1) AS "Downvote Rate %"
FROM analytics_daily_metrics
WHERE metric_date >= $__timeFrom()::date AND metric_date <= $__timeTo()::date;
```

### Core Panel 4: Daily Translation Volume by Language Pair (Time Series)
```sql
SELECT 
  metric_date AS "time",
  concat(source_language, '->', target_language) AS metric,
  sum(total_requests) AS value
FROM analytics_daily_metrics
WHERE metric_date >= $__timeFrom()::date AND metric_date <= $__timeTo()::date
GROUP BY metric_date, source_language, target_language
ORDER BY metric_date ASC;
```

### Core Panel 5: Average Latency by Language Pair (Bar Gauge)
```sql
SELECT 
  concat(source_language, '->', target_language) AS "Language Pair",
  round(avg(avg_latency_ms)::numeric, 0) AS "Mean Latency (ms)",
  round(max(p95_latency_ms)::numeric, 0) AS "P95 Latency (ms)"
FROM analytics_daily_metrics
WHERE metric_date >= $__timeFrom()::date AND metric_date <= $__timeTo()::date
GROUP BY source_language, target_language
ORDER BY "Mean Latency (ms)" DESC;
```

### Core Panel 6: Quality Tier Distribution (Donut Chart)
```sql
SELECT 
  CASE 
    WHEN avg_quality_score >= 85 THEN 'EXCELLENT'
    WHEN avg_quality_score >= 70 THEN 'GOOD'
    WHEN avg_quality_score >= 50 THEN 'NEEDS_REVIEW'
    ELSE 'POOR'
  END AS "Quality Tier",
  sum(total_requests) AS "Count"
FROM analytics_daily_metrics
WHERE metric_date >= $__timeFrom()::date AND metric_date <= $__timeTo()::date
GROUP BY 1;
```

### Core Panel 7: Feedback Failure Reason Distribution (Horizontal Bar)
```sql
SELECT 
  f.reason AS "Defect Classification",
  count(f.id) AS "Report Count"
FROM feedback f
WHERE f.rating = 'POOR' AND f.created_at >= $__timeFrom()
GROUP BY f.reason
ORDER BY "Report Count" DESC;
```

### Secondary Panel 8: Volume by Provider (Donut / Bar)
```sql
SELECT 
  provider AS "Provider",
  sum(total_requests) AS "Requests"
FROM analytics_daily_metrics
WHERE metric_date >= $__timeFrom()::date AND metric_date <= $__timeTo()::date
GROUP BY provider
ORDER BY "Requests" DESC;
```

### Secondary Panel 9: Average Latency by Provider (Bar Gauge)
```sql
SELECT 
  provider AS "Provider",
  round(avg(avg_latency_ms)::numeric, 0) AS "Avg Latency (ms)"
FROM analytics_daily_metrics
WHERE metric_date >= $__timeFrom()::date AND metric_date <= $__timeTo()::date
GROUP BY provider;
```

### Panel 10: Live Anomaly Triage Table
```sql
SELECT 
  a.detected_at AS "Timestamp",
  t.provider AS "Provider",
  concat(t.source_language, '->', t.target_language) AS "Pair",
  a.anomaly_type AS "Anomaly Type",
  a.anomaly_score AS "Severity Score",
  a.diagnostic_details AS "Diagnostic Context",
  left(t.source_text, 60) AS "Source Snippet"
FROM analytics_anomalies a
JOIN translations t ON a.translation_id = t.id
ORDER BY a.detected_at DESC
LIMIT 50;
```

---

## 4. Alerting Thresholds & Notification Rules
1. **High Downvote Alert**:
   - Condition: `poor_feedback_rate > 0.15` (15%) for any language pair over a 24-hour window.
   - Severity: `Warning`.
2. **Latency Degradation Alert**:
   - Condition: `p95_latency_ms > 4500` ms over 1 hour.
   - Severity: `Critical` (Indicates provider throttling or networking degradation).
3. **Severe Anomaly Cluster Alert**:
   - Condition: More than 20 `LENGTH_TRUNCATION` anomalies detected within a single batch run.
   - Severity: `Warning`.
