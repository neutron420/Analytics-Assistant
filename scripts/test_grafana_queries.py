from src.database.connection import get_db_session
from sqlalchemy import text

queries = {
    "1. Daily Translation Volume": """
        SELECT 
            date_trunc('day', created_at) AS metric_date,
            count(*) AS total_requests
        FROM translations
        GROUP BY 1
        ORDER BY 1 DESC;
    """,
    "2. Top 5 Language Pairs": """
        SELECT 
            concat(upper(source_language), ' -> ', upper(target_language)) AS "Language Pair",
            count(*) AS "Total Requests"
        FROM translations
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT 5;
    """,
    "3. Avg Translation Time by Pair": """
        SELECT 
            concat(upper(source_language), ' -> ', upper(target_language)) AS "Language Pair",
            round(avg(translation_time_ms)::numeric, 1) AS "Avg Latency ms"
        FROM translations
        GROUP BY 1
        ORDER BY 2 DESC;
    """,
    "4. Poor-Quality Reports Over Time": """
        SELECT 
            date_trunc('day', f.created_at) AS metric_date,
            count(*) AS "Poor Reports"
        FROM feedback f
        WHERE upper(f.rating) = 'POOR'
        GROUP BY 1
        ORDER BY 1 DESC;
    """,
    "5. Avg Confidence by Pair": """
        SELECT 
            concat(upper(t.source_language), ' -> ', upper(t.target_language)) AS "Language Pair",
            round(avg(COALESCE(o.confidence_score, 0.88))::numeric, 2) AS "Avg Confidence"
        FROM translations t
        JOIN translation_options o ON o.translation_id = t.id
        GROUP BY 1
        ORDER BY 2 DESC;
    """,
    "6. Quality Distribution": """
        SELECT 
            upper(rating) AS "Rating",
            count(*) AS "Feedback Count"
        FROM feedback
        GROUP BY 1;
    """,
    "7. Feedback Reason Distribution": """
        SELECT 
            COALESCE(reason, 'UNSPECIFIED') AS "Defect Reason",
            count(*) AS "Defects"
        FROM feedback
        WHERE upper(rating) = 'POOR'
        GROUP BY 1
        ORDER BY 2 DESC;
    """,
    "8. Preferred Translation Style": """
        SELECT 
            style_option AS "Style",
            count(*) AS "Selections"
        FROM translation_options
        WHERE user_selected = TRUE
        GROUP BY 1
        ORDER BY 2 DESC;
    """,
    "9. Anomaly Count Over Time": """
        SELECT 
            date_trunc('day', created_at) AS metric_date,
            count(*) AS "Anomalies"
        FROM translations
        WHERE anomaly_flag = TRUE
        GROUP BY 1
        ORDER BY 1 DESC;
    """,
    "10. Translation Latency Trend": """
        SELECT 
            created_at AS time,
            translation_time_ms AS "Latency ms"
        FROM translations
        ORDER BY created_at ASC;
    """,
    "11. Provider Request Volume": """
        SELECT 
            provider AS "Provider",
            count(*) AS "Requests"
        FROM translations
        GROUP BY 1
        ORDER BY 2 DESC;
    """,
    "12. Provider Error Count": """
        SELECT 
            provider AS "Provider",
            count(CASE WHEN status != 'COMPLETED' THEN 1 END) AS "Errors"
        FROM translations
        GROUP BY 1;
    """,
    "13. Quality Score Distribution": """
        SELECT 
            CASE 
                WHEN quality_score >= 88 THEN 'EXCELLENT'
                WHEN quality_score >= 75 THEN 'GOOD'
                WHEN quality_score >= 60 THEN 'NEEDS_REVIEW'
                ELSE 'POOR'
            END AS "Category",
            count(*) AS "Count"
        FROM translations
        WHERE quality_score IS NOT NULL
        GROUP BY 1
        ORDER BY 2 DESC;
    """,
    "14. Data Quality / ETL Summary": """
        SELECT 
            to_char(metric_date, 'YYYY-MM-DD') AS "Metric Date",
            sum(total_requests) AS "Total Records",
            round(avg(avg_latency_ms)::numeric, 1) AS "Avg Latency ms",
            round(avg(avg_quality_score)::numeric, 1) AS "Quality Score",
            sum(poor_feedback_count) AS "Poor Feedback Count"
        FROM analytics_daily_metrics
        GROUP BY 1
        ORDER BY 1 DESC
        LIMIT 10;
    """
}

def test_queries():
    with get_db_session() as sess:
        for name, q in queries.items():
            res = sess.execute(text(q)).fetchall()
            print(f"Query [{name}] SUCCESS, returned {len(res)} rows.")

if __name__ == "__main__":
    test_queries()
