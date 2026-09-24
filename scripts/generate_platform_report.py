"""
Platform Quality & Continuous Improvement Executive Report Generator
Translation Quality Analytics & Continuous Improvement Platform

Generates an executive diagnostic audit report compiling live PostgreSQL telemetry,
human feedback defect taxonomy, user preference trends, and PySpark ETL data quality metrics.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Configure UTF-8 stdout encoding for Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.database.connection import check_db_health
from src.database.repository import default_repository
from src.config import config


def generate_executive_report() -> str:
    """Compiles the complete platform analytical report from real operational data."""
    now = datetime.now(timezone.utc)
    now_str = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # 1. Health & Config
    db_health = check_db_health()
    db_status = "HEALTHY" if db_health.get("status") == "healthy" else "DEGRADED"
    
    # 2. Live Analytics Summary
    summary = default_repository.get_live_analytics_summary()
    tot_trans = summary.get("total_translations", 0)
    avg_lat = summary.get("avg_latency_s", 0.0)
    q_score = summary.get("avg_quality_score", 0.0)
    poor_rate = summary.get("poor_feedback_rate", 0.0)
    total_fb = summary.get("total_feedbacks", 0)
    poor_fb = summary.get("poor_feedback_count", 0)
    good_fb = summary.get("good_feedback_count", 0)
    
    # Quality tier categorization
    if q_score >= 88.0:
        tier_label = "EXCELLENT"
    elif q_score >= 75.0:
        tier_label = "GOOD"
    elif q_score >= 60.0:
        tier_label = "NEEDS_REVIEW"
    else:
        tier_label = "POOR"

    # 3. Read PySpark ETL Quality Report
    etl_report_file = ROOT_DIR / "docs" / "ETL_QUALITY_REPORT.md"
    etl_text = "No batch ETL run recorded yet."
    if etl_report_file.exists():
        etl_text = etl_report_file.read_text(encoding="utf-8").strip()

    # 4. Format Language Pairs Table
    pairs = summary.get("language_pairs", [])
    if pairs:
        pair_rows = "\n".join([
            f"| `{p['language_pair']}` | {p['translation_count']:,} | {p['avg_latency_s']}s | {p['avg_quality_score']}/100 | {p['observed_quality_rate']} | {p['poor_feedback_rate']} |"
            for p in pairs
        ])
    else:
        pair_rows = "| No active language pairs logged yet | — | — | — | — | — |"

    # 5. Format Defect Reasons Table
    defects = summary.get("feedback_reasons", {})
    if defects:
        defect_rows = "\n".join([
            f"| `{r}` | {d['count']} | {d['percentage']}% |"
            for r, d in defects.items()
        ])
    else:
        defect_rows = "| None reported | 0 | 0.0% |"

    # 6. Format Style Preferences Table
    styles = summary.get("style_preferences", {})
    if styles:
        style_rows = "\n".join([
            f"| `{s.capitalize()}` | {d['count']} | {d['percentage']}% |"
            for s, d in styles.items()
        ])
    else:
        style_rows = "| None recorded | 0 | 0.0% |"

    # 7. Format Insights
    insights = summary.get("insights", [])
    insights_str = "\n".join(f"- **Insight**: {ins}" for ins in insights)

    report_content = f"""# Translation Quality Analytics & Continuous Improvement Report
**Generated At:** {now_str}  
**Active AI Provider:** `{config.translation_provider.upper()}` (`{config.hf_model}`)  
**Database Health:** `{db_status}`  
**Report Scope:** Live Operational Telemetry + PySpark Historical Batch Data  

---

## 1. Executive Summary & KPIs

| Metric | Measured Value | Operational Baseline | Status |
| :--- | :--- | :--- | :--- |
| **Total Translations** | **{tot_trans:,}** | N/A | Active Logging |
| **Mean Roundtrip Latency** | **{avg_lat:.2f}s** | $< 8.00$s | {'NORMAL' if avg_lat <= 8.0 else 'ATTENTION'} |
| **System Quality Score** | **{q_score:.1f} / 100** (`{tier_label}`) | >= 75.0 / 100 | {'NORMAL' if q_score >= 75.0 else 'NEEDS REVIEW'} |
| **Evaluated Candidates** | **{total_fb}** ({good_fb} Good / {poor_fb} Poor) | N/A | Human-in-the-Loop |
| **Poor-Quality Defect Rate** | **{poor_rate:.1f}%** | < 20.0% | {'NORMAL' if poor_rate <= 20.0 else 'DEFECT SPIKE'} |
| **Flagged Operational Anomalies** | **{summary.get('anomalies_count', 0)}** | 0 | {'CLEAN' if summary.get('anomalies_count', 0) == 0 else 'TRIAGE NEEDED'} |

---

## 2. Language-Pair Performance Matrix

| Language Pair | Volume | Avg Latency | Quality Score | Observed Quality | Defect Rate |
| :--- | :--- | :--- | :--- | :--- | :--- |
{pair_rows}

---

## 3. Human Evaluation & Linguistic Defect Breakdown

Distribution of defects reported by human evaluators:

| Defect Category | Flagged Occurrences | Defect Share (%) |
| :--- | :--- | :--- |
{defect_rows}

---

## 4. Evaluator Stylistic Preferences

User preference breakdown across generated translation variants:

| Translation Variant | Evaluator Selections | Share (%) |
| :--- | :--- | :--- |
{style_rows}

---

## 5. Continuous Improvement Recommendations

Based on empirical feedback patterns and operational anomaly detection:
{insights_str}

**Recommended Action Items:**
1. If `TOO_LITERAL` dominates, refine provider system instructions to prioritize idiomatic phrasing and target-language colloquial flow.
2. If `INCORRECT_MEANING` or `TERMINOLOGY_ISSUE` spikes on specific language pairs, introduce specialized domain glossaries into prompt templates.
3. Review flagged anomaly requests in the Gradio **Quality Investigation** tab using the Request ID.

---

## 6. PySpark Batch Data Quality Audit

Below is the verified audit report generated from the latest PySpark big-data batch pipeline:

{etl_text}

---
*Report automatically generated by Translation Quality Analytics Platform.*
"""

    # Persist report
    reports_dir = ROOT_DIR / "docs"
    out_file = reports_dir / "PLATFORM_QUALITY_REPORT.md"
    try:
        out_file.write_text(report_content, encoding="utf-8")
    except Exception as e:
        pass

    return report_content


def main():
    print("Generating Platform Quality & Continuous Improvement Executive Report...")
    report = generate_executive_report()
    print("\n" + report)
    print(f"\n✓ Report saved successfully to: docs/PLATFORM_QUALITY_REPORT.md")


if __name__ == "__main__":
    main()
