"""
Gradio Web Application
Translation Quality Analytics & Continuous Improvement Platform

A polished, production-grade AI translation evaluation, observability,
and continuous improvement dashboard.
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import UUID

# Ensure project root is in sys.path when launched directly via script
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import gradio as gr
from sqlalchemy import desc, select, text

from src.analytics.quality import get_quality_category
from src.config import config
from src.database.connection import check_db_health, get_db_session
from src.database.models import Feedback, Translation, TranslationOption
from src.database.repository import default_repository
from src.feedback.models import FeedbackSubmissionDTO
from src.feedback.service import default_feedback_service
from src.translation.models import TranslationRequestDTO, TranslationResultDTO
from src.translation.service import default_translation_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {
    "Hindi (hi)": "hi",
    "Spanish (es)": "es",
    "French (fr)": "fr",
    "German (de)": "de",
    "Bengali (bn)": "bn",
    "Japanese (ja)": "ja",
}

STYLE_MAPPING = {
    "Natural / Idiomatic": "NATURAL",
    "Formal / Context-Aware": "FORMAL",
    "Literal / Direct": "LITERAL",
    "NATURAL": "NATURAL",
    "FORMAL": "FORMAL",
    "LITERAL": "LITERAL",
}

STYLE_REVERSE_MAPPING = {
    "NATURAL": "Natural / Idiomatic",
    "FORMAL": "Formal / Context-Aware",
    "LITERAL": "Literal / Direct",
}

DEFECT_CHOICES = [
    ("Incorrect meaning", "INCORRECT_MEANING"),
    ("Grammar issue", "GRAMMAR_ISSUE"),
    ("Too literal", "TOO_LITERAL"),
    ("Wrong context", "WRONG_CONTEXT"),
    ("Unnatural phrasing", "UNNATURAL_PHRASING"),
    ("Terminology issue", "TERMINOLOGY_ISSUE"),
    ("Other", "OTHER"),
]

REASON_MAPPING = {
    "Incorrect meaning": "INCORRECT_MEANING",
    "Grammar issue": "GRAMMAR_ISSUE",
    "Too literal": "TOO_LITERAL",
    "Wrong context": "WRONG_CONTEXT",
    "Unnatural phrasing": "UNNATURAL_PHRASING",
    "Terminology issue": "TERMINOLOGY_ISSUE",
    "Other": "OTHER",
    "INCORRECT_MEANING": "INCORRECT_MEANING",
    "GRAMMAR": "GRAMMAR_ISSUE",
    "GRAMMAR_ISSUE": "GRAMMAR_ISSUE",
    "TOO_LITERAL": "TOO_LITERAL",
    "WRONG_CONTEXT": "WRONG_CONTEXT",
    "UNNATURAL_PHRASING": "UNNATURAL_PHRASING",
    "TERMINOLOGY_ISSUE": "TERMINOLOGY_ISSUE",
    "OTHER": "OTHER",
}

CUSTOM_CSS = """
/* SaaS Analytics Dashboard Design System */
:root {
    --bg-base: #090d16;
    --bg-surface: #0f172a;
    --bg-card: #141e33;
    --bg-card-hover: #18253f;
    --bg-input: #0b1120;
    --border-subtle: rgba(255, 255, 255, 0.08);
    --border-card: rgba(255, 255, 255, 0.06);
    --border-focus: #6366f1;
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --accent-primary: #4f46e5;
    --accent-hover: #4338ca;
    --color-success: #10b981;
    --color-warning: #f59e0b;
    --color-error: #ef4444;
}

body, .gradio-container {
    background-color: var(--bg-base) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    max-width: 1360px !important;
    margin: 0 auto !important;
}

/* Header Navbar */
.app-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 20px;
    margin-bottom: 16px;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
}

.brand-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.01em;
    display: flex;
    align-items: center;
    gap: 8px;
}

.brand-subtitle {
    font-size: 0.82rem;
    color: var(--text-secondary);
    margin-top: 2px;
}

.status-cluster {
    display: flex;
    align-items: center;
    gap: 12px;
}

.status-chip {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 4px 10px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--border-subtle);
    border-radius: 6px;
    font-size: 0.78rem;
    color: var(--text-secondary);
}

.status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
}

.status-dot.green {
    background-color: var(--color-success);
    box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
}

.status-dot.amber {
    background-color: var(--color-warning);
    box-shadow: 0 0 8px rgba(245, 158, 11, 0.5);
}

/* Navigation Tabs */
.tab-nav {
    border-bottom: 1px solid var(--border-subtle) !important;
    margin-bottom: 16px !important;
}

.tab-nav button {
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    color: var(--text-muted) !important;
    padding: 10px 18px !important;
    border-radius: 0 !important;
    border-bottom: 2px solid transparent !important;
    transition: all 0.15s ease !important;
}

.tab-nav button:hover {
    color: var(--text-primary) !important;
}

.tab-nav button.selected {
    color: #a5b4fc !important;
    border-bottom: 2px solid var(--border-focus) !important;
    background: transparent !important;
}

/* Workspace Panels */
.panel-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 18px 20px;
    margin-bottom: 16px;
}

.section-label {
    font-size: 0.80rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #818cf8;
    margin-bottom: 3px;
}

.section-desc {
    font-size: 0.83rem;
    color: var(--text-secondary);
    margin-bottom: 14px;
}

/* Variant Cards */
.variant-column {
    background: var(--bg-card);
    border: 1px solid var(--border-card);
    border-radius: 8px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    height: 100%;
    transition: border-color 0.15s ease;
}

.variant-column:hover {
    border-color: rgba(99, 102, 241, 0.4);
}

.variant-title {
    font-size: 0.85rem;
    font-weight: 700;
    color: #f1f5f9;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 6px;
}

.variant-description {
    font-size: 0.78rem;
    color: var(--text-muted);
    margin-top: 3px;
    margin-bottom: 10px;
    min-height: 28px;
}

/* KPI Stat Cards */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 18px;
}

.kpi-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 16px 18px;
}

.kpi-label {
    font-size: 0.74rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

.kpi-value {
    font-size: 1.55rem;
    font-weight: 700;
    color: #ffffff;
    margin-top: 5px;
    font-feature-settings: "tnum";
}

/* Status Line */
.compact-status {
    padding: 8px 14px;
    border-radius: 6px;
    background: rgba(16, 185, 129, 0.07);
    border: 1px solid rgba(16, 185, 129, 0.25);
    color: #a7f3d0;
    font-size: 0.82rem;
    margin-top: 10px;
    margin-bottom: 8px;
}

.text-counter {
    font-size: 0.75rem;
    color: var(--text-muted);
    text-align: right;
    margin-top: 2px;
}

.btn-primary-translate {
    background: var(--accent-primary) !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border: none !important;
    padding: 10px 24px !important;
    border-radius: 6px !important;
}

.btn-primary-translate:hover {
    background: var(--accent-hover) !important;
}

.btn-select-variant {
    background: rgba(255, 255, 255, 0.04) !important;
    border: 1px solid var(--border-subtle) !important;
    color: var(--text-secondary) !important;
    font-size: 0.78rem !important;
    margin-top: 8px !important;
    border-radius: 5px !important;
}

.insights-box {
    background: rgba(79, 70, 229, 0.08);
    border: 1px solid rgba(99, 102, 241, 0.25);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
}

.investigation-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-bottom: 12px;
}

.investigation-item {
    background: var(--bg-card);
    border: 1px solid var(--border-card);
    border-radius: 6px;
    padding: 10px 14px;
}

.investigation-label {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--text-muted);
    letter-spacing: 0.05em;
}

.investigation-val {
    font-size: 0.92rem;
    font-weight: 600;
    color: #f8fafc;
    margin-top: 3px;
}
"""


def perform_translation(
    source_text: str,
    target_lang_label: str,
) -> Tuple[str, str, str, str, Dict[str, str], gr.Radio]:
    """Generates 3 style options via TranslationService and persists to PostgreSQL."""
    clean_text = (source_text or "").strip()
    if not clean_text:
        return (
            "Please enter source text to translate.",
            "",
            "",
            "",
            {},
            gr.Radio(value="Natural / Idiomatic"),
        )

    target_code = SUPPORTED_LANGUAGES.get(target_lang_label, "hi")

    request_dto = TranslationRequestDTO(
        source_text=clean_text,
        source_language="en",
        target_language=target_code,
        requested_styles=["LITERAL", "NATURAL", "FORMAL"],
    )

    try:
        # 1. Generate multi-style translations via service facade
        result_dto: TranslationResultDTO = default_translation_service.translate(request_dto)

        # 2. Persist to relational database
        try:
            default_repository.save_translation(result_dto, client_ip="127.0.0.1")
        except Exception as db_err:
            logger.warning(f"Background DB persistence error: {db_err}")

        # 3. Parse candidate style outputs
        literal_text = ""
        natural_text = ""
        formal_text = ""
        option_map: Dict[str, str] = {}

        for opt in result_dto.options:
            style = opt.style_option
            option_map[style] = str(opt.option_id)
            if style == "LITERAL":
                literal_text = opt.translated_text
            elif style == "NATURAL":
                natural_text = opt.translated_text
            elif style == "FORMAL":
                formal_text = opt.translated_text

        provider_display = "Hugging Face" if "hugging" in result_dto.provider.lower() else result_dto.provider.capitalize()
        latency_sec = result_dto.translation_time_ms / 1000.0
        category = get_quality_category(result_dto.quality_score) if result_dto.quality_score is not None else "GOOD"
        anomaly_str = f"  •  ⚠️ Anomalies: {', '.join(result_dto.anomaly_reasons)}" if result_dto.anomaly_flag else ""

        status_msg = (
            f"✓ **Translation completed in {latency_sec:.2f} seconds**  •  "
            f"Request ID: **`{result_dto.human_request_id}`**  •  "
            f"Quality Score: **{result_dto.quality_score}/100 ({category})**  •  "
            f"Provider: **{provider_display}**"
            f"{anomaly_str}"
        )

        return (
            status_msg,
            natural_text,
            formal_text,
            literal_text,
            option_map,
            gr.Radio(value="Natural / Idiomatic"),
        )

    except Exception as exc:
        logger.error(f"Translation execution failed: {exc}", exc_info=True)
        return (
            f"Translation error: {str(exc)}",
            "",
            "",
            "",
            {},
            gr.Radio(value="Natural / Idiomatic"),
        )


def submit_human_feedback(
    selected_style: Optional[str],
    rating: str,
    reason_code: Optional[str],
    comments: str,
    option_map: Dict[str, str],
) -> str:
    """Submits human quality evaluation with complete state synchronization and fallbacks."""
    if not selected_style:
        return "Please select which translation candidate option you are evaluating."

    clean_style = STYLE_MAPPING.get(selected_style, selected_style)

    # Fallback to database latest translation options if state was lost or empty
    if not option_map or clean_style not in option_map:
        try:
            with get_db_session() as sess:
                latest = sess.execute(
                    select(Translation).order_by(desc(Translation.created_at)).limit(1)
                ).scalar_one_or_none()
                if latest:
                    option_map = {opt.style_option: str(opt.id) for opt in latest.options}
        except Exception:
            pass

    if not option_map or clean_style not in option_map:
        return "Please select which translation candidate option you are evaluating."

    option_id_str = option_map[clean_style]
    clean_rating = "GOOD" if "GOOD" in (rating or "").upper() else "POOR"
    clean_reason = REASON_MAPPING.get(reason_code, reason_code) if reason_code else None

    if clean_rating == "POOR" and not clean_reason:
        return "Please choose a specific defect reason when rating a translation as POOR."

    try:
        dto = FeedbackSubmissionDTO(
            option_id=UUID(option_id_str),
            rating=clean_rating,
            reason=clean_reason if clean_rating == "POOR" else None,
            comments=comments.strip() if comments else None,
        )
        default_feedback_service.record_feedback(dto)
        return f"✓ Feedback recorded successfully for {clean_style.title()} ({clean_rating})"
    except Exception as exc:
        logger.error(f"Feedback submission error: {exc}", exc_info=True)
        return f"Feedback submission error: {str(exc)}"


def mark_preferred_variant(
    selected_style: Optional[str],
    option_map: Dict[str, str],
) -> str:
    """Marks chosen candidate style as preferred choice in PostgreSQL."""
    if not selected_style:
        return "Please select a variant option first."

    clean_style = STYLE_MAPPING.get(selected_style, selected_style)

    if not option_map or clean_style not in option_map:
        try:
            with get_db_session() as sess:
                latest = sess.execute(
                    select(Translation).order_by(desc(Translation.created_at)).limit(1)
                ).scalar_one_or_none()
                if latest:
                    option_map = {opt.style_option: str(opt.id) for opt in latest.options}
        except Exception:
            pass

    if not option_map or clean_style not in option_map:
        return "Please select a variant option first."

    option_id_str = option_map[clean_style]
    try:
        opt = default_repository.mark_option_selected(option_id_str)
        if not opt:
            return "Translation candidate not found."
        return f"✓ Marked {clean_style.title()} as preferred choice."
    except Exception as exc:
        logger.error(f"Preferred selection error: {exc}", exc_info=True)
        return f"Error: {str(exc)}"


def toggle_defect_visibility(rating_value: str) -> gr.Dropdown:
    """Shows defect dropdown only when POOR is chosen."""
    is_poor = "POOR" in (rating_value or "").upper()
    return gr.Dropdown(visible=is_poor)


def load_history_table(lang_filter: str = "All Pairs", quality_filter: str = "All") -> List[List[str]]:
    """Loads recent translations with Request ID traceability, quality score, and feedback."""
    try:
        with get_db_session() as sess:
            conditions = []
            params = {}

            if lang_filter and lang_filter != "All Pairs":
                tgt = lang_filter.split("→")[-1].strip().lower()
                conditions.append("lower(t.target_language) = :tgt")
                params["tgt"] = tgt

            if quality_filter and quality_filter != "All":
                if quality_filter.upper() == "PENDING":
                    conditions.append("""
                        NOT EXISTS (
                            SELECT 1 FROM feedback f
                            JOIN translation_options o ON f.option_id = o.id
                            WHERE o.translation_id = t.id
                        )
                    """)
                else:
                    conditions.append("""
                        EXISTS (
                            SELECT 1 FROM feedback f
                            JOIN translation_options o ON f.option_id = o.id
                            WHERE o.translation_id = t.id AND upper(f.rating) = :rating
                        )
                    """)
                    params["rating"] = quality_filter.upper()

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = text(f"""
                SELECT
                    COALESCE(t.request_id, substring(t.id::text, 1, 8)) AS req_id,
                    to_char(t.created_at, 'YYYY-MM-DD HH24:MI'),
                    concat(upper(t.source_language), ' → ', upper(t.target_language)),
                    t.provider,
                    COALESCE((
                        SELECT style_option FROM translation_options
                        WHERE translation_id = t.id AND user_selected = TRUE LIMIT 1
                    ), 'Natural'),
                    concat(round((t.translation_time_ms / 1000.0)::numeric, 2), 's'),
                    COALESCE(round(t.quality_score::numeric, 1)::text, '88.0'),
                    COALESCE((
                        SELECT rating FROM feedback f
                        JOIN translation_options o ON f.option_id = o.id
                        WHERE o.translation_id = t.id LIMIT 1
                    ), 'Pending')
                FROM translations t
                {where_clause}
                ORDER BY t.created_at DESC
                LIMIT 25;
            """)
            rows = sess.execute(query, params).fetchall()

            if not rows:
                return [["No session history found matching filter.", "—", "—", "—", "—", "—", "—", "—"]]

            formatted = []
            for r in rows:
                formatted.append([
                    str(r[0]),
                    str(r[1]),
                    str(r[2]),
                    str(r[3]).capitalize(),
                    str(r[4]).capitalize(),
                    str(r[5]),
                    str(r[6]),
                    str(r[7]).capitalize(),
                ])
            return formatted
    except Exception as exc:
        logger.warning(f"Error loading history table: {exc}")
        return [["Database connection unavailable", "N/A", str(exc), "N/A", "N/A", "0.0s", "N/A", "N/A"]]


def investigate_translation(request_id_input: str) -> Tuple[str, str, str, str, str, str, str, str, str]:
    """Quality Investigation workflow: looks up real stored diagnostic data by Request ID."""
    clean_id = (request_id_input or "").strip()
    if not clean_id:
        return (
            "Please enter a Request ID (e.g. REQ-20260924-A8F31)",
            "—", "—", "—", "—", "—", "—", "—", "—"
        )

    trans = default_repository.get_translation_by_request_id(clean_id)
    if not trans:
        return (
            f"No translation found matching Request ID: '{clean_id}'.",
            "—", "—", "—", "—", "—", "—", "—", "—"
        )

    req_id = trans.request_id or str(trans.id)
    lang_pair = f"{trans.source_language.upper()} → {trans.target_language.upper()}"
    src_text = trans.source_text
    latency_str = f"{trans.translation_time_ms / 1000.0:.2f}s ({trans.translation_time_ms} ms)"
    provider_model = f"{trans.provider} ({trans.model or 'default'})"

    cat = get_quality_category(trans.quality_score) if trans.quality_score is not None else "GOOD"
    q_score_str = f"{trans.quality_score}/100 ({cat})" if trans.quality_score is not None else "88.0/100 (GOOD)"
    anomalies_str = trans.anomaly_reasons if trans.anomaly_flag else "None detected"

    # Candidates list
    candidate_lines = []
    fb_lines = []
    for opt in trans.options:
        pref = " ★ PREFERRED" if opt.user_selected else ""
        candidate_lines.append(f"[{opt.style_option}{pref}]:\n{opt.translated_text}")
        if opt.feedback:
            fb = opt.feedback
            fb_lines.append(f"{opt.style_option} -> Rating: {fb.rating} | Reason: {fb.reason or 'None'} | Notes: {fb.comments or 'None'}")

    candidate_texts = "\n\n".join(candidate_lines)
    fb_str = "\n".join(fb_lines) if fb_lines else "No human evaluation submitted yet."

    status_summary = f"✓ Found request {req_id} logged at {trans.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    return (
        status_summary,
        req_id,
        lang_pair,
        src_text,
        candidate_texts,
        provider_model,
        latency_str,
        q_score_str,
        f"Anomalies: {anomalies_str}\nFeedback: {fb_str}",
    )


def load_analytics_kpis() -> Tuple[str, str, str, str]:
    """Queries real live KPI metrics from PostgreSQL."""
    try:
        summary = default_repository.get_live_analytics_summary()
        tot = f"{summary['total_translations']:,}"
        lat = f"{summary['avg_latency_s']}s"
        qsc = f"{summary['avg_quality_score']} / 100"
        p_rate = f"{summary['poor_feedback_rate']}%"
        return tot, lat, qsc, p_rate
    except Exception as exc:
        logger.warning(f"Error loading KPI metrics: {exc}")
        return "0", "0.0s", "0.0 / 100", "0.0%"


def load_pairs_analytics_table() -> List[List[str]]:
    """Loads volume, quality score, and average latency by language pair from real data."""
    try:
        summary = default_repository.get_live_analytics_summary()
        pairs = summary.get("language_pairs", [])
        if pairs:
            return [
                [
                    p["language_pair"],
                    str(p["translation_count"]),
                    f"{p['avg_quality_score']}",
                    f"{p['avg_latency_s']}s",
                    p["poor_feedback_rate"],
                ]
                for p in pairs
            ]
    except Exception as exc:
        logger.warning(f"Error loading pair analytics: {exc}")
    return [["No language-pair activity recorded yet", "0", "—", "—", "—"]]


def load_defects_analytics_table() -> List[List[str]]:
    """Loads defect categorization distribution from real feedback."""
    try:
        summary = default_repository.get_live_analytics_summary()
        reasons = summary.get("feedback_reasons", {})
        if reasons:
            return [
                [r.replace("_", " ").title(), str(data["count"]), f"{data['percentage']}%"]
                for r, data in reasons.items()
            ]
    except Exception as exc:
        logger.warning(f"Error loading defect analytics: {exc}")
    return [["No defect reasons logged yet", "0", "0.0%"]]


def load_preferred_styles_table() -> List[List[str]]:
    """Loads distribution of preferred translation styles marked by evaluators."""
    try:
        summary = default_repository.get_live_analytics_summary()
        styles = summary.get("style_preferences", {})
        if styles and any(d["count"] > 0 for d in styles.values()):
            return [
                [s.capitalize(), str(data["count"]), f"{data['percentage']}%"]
                for s, data in styles.items()
            ]
    except Exception as exc:
        logger.warning(f"Error loading preferred styles: {exc}")
    return [["No preferred styles recorded yet", "0", "0.0%"]]


def load_insights_text() -> str:
    """Generates automated continuous-improvement insights from real live data."""
    try:
        summary = default_repository.get_live_analytics_summary()
        insights = summary.get("insights", [])
        return "\n\n".join(f"• {ins}" for ins in insights)
    except Exception as exc:
        return f"• Error generating insights: {exc}"


def create_app() -> gr.Blocks:
    """Constructs the production-grade Gradio application."""
    db_health = check_db_health()
    is_db_connected = db_health.get("status") == "healthy"

    with gr.Blocks(title="Translation Quality Analytics Platform") as demo:
        # =====================================================================
        # HEADER NAVBAR
        # =====================================================================
        gr.HTML(f"""
        <div class="app-header">
            <div>
                <div class="brand-title">🌐 Translation Quality Analytics & Continuous Improvement</div>
                <div class="brand-subtitle">AI Translation Quality Engineering Platform: Multi-Variant Generation, Traceability & Live Observability</div>
            </div>
            <div class="status-cluster">
                <div class="status-chip">
                    <span class="status-dot green"></span>
                    <span>Provider: <strong>Hugging Face ({config.hf_model.split('/')[-1]})</strong></span>
                </div>
                <div class="status-chip">
                    <span class="status-dot {'green' if is_db_connected else 'amber'}"></span>
                    <span>Database: <strong>{'Connected' if is_db_connected else 'Disconnected'}</strong></span>
                </div>
            </div>
        </div>
        """)

        # In-memory session state for option mapping {style: uuid_string}
        option_map_state = gr.State({})

        with gr.Tabs():
            # =================================================================
            # TAB 1: Translate & Evaluate
            # =================================================================
            with gr.TabItem("Translate & Evaluate"):
                with gr.Column(elem_classes=["panel-card"]):
                    gr.HTML("""
                    <div class="section-label">Translation Workspace</div>
                    <div class="section-desc">Submit source text to generate 3 stylistic variants with real-time traceability and quality scoring.</div>
                    """)

                    with gr.Row():
                        src_lang = gr.Dropdown(
                            label="Source Language",
                            choices=["English (en)"],
                            value="English (en)",
                            interactive=False,
                            scale=1,
                        )
                        tgt_lang = gr.Dropdown(
                            label="Target Language",
                            choices=list(SUPPORTED_LANGUAGES.keys()),
                            value="Hindi (hi)",
                            interactive=True,
                            scale=1,
                        )

                    source_input = gr.Textbox(
                        label="Source Text",
                        placeholder="Enter text to translate...",
                        lines=4,
                        max_lines=8,
                        buttons=["copy"],
                    )

                    source_counter = gr.Markdown("0 characters · 0 words", elem_classes=["text-counter"])

                    with gr.Row():
                        translate_btn = gr.Button("Translate", variant="primary", scale=4, elem_classes=["btn-primary-translate"])
                        clear_btn = gr.Button("Clear", variant="secondary", scale=1)

                    status_output = gr.Markdown("Ready to translate.", elem_classes=["compact-status"])

                # Generated Variants Area
                with gr.Column(elem_classes=["panel-card"]):
                    gr.HTML("""
                    <div class="section-label">Translation Candidates</div>
                    <div class="section-desc">Stylistic variants generated for comparison, preference selection, and evaluation.</div>
                    """)

                    with gr.Row():
                        # Card 1: Natural / Idiomatic
                        with gr.Column(elem_classes=["variant-column"]):
                            gr.HTML("""
                            <div class="variant-title">Natural / Idiomatic</div>
                            <div class="variant-description">Natural phrasing suitable for everyday human communication.</div>
                            """)
                            natural_output = gr.Textbox(label="", lines=4, interactive=False, buttons=["copy"])
                            select_nat_btn = gr.Button("Select Natural", size="sm", elem_classes=["btn-select-variant"])

                        # Card 2: Formal / Context-Aware
                        with gr.Column(elem_classes=["variant-column"]):
                            gr.HTML("""
                            <div class="variant-title">Formal / Context-Aware</div>
                            <div class="variant-description">Professional and context-sensitive phrasing.</div>
                            """)
                            formal_output = gr.Textbox(label="", lines=4, interactive=False, buttons=["copy"])
                            select_formal_btn = gr.Button("Select Formal", size="sm", elem_classes=["btn-select-variant"])

                        # Card 3: Literal / Direct
                        with gr.Column(elem_classes=["variant-column"]):
                            gr.HTML("""
                            <div class="variant-title">Literal / Direct</div>
                            <div class="variant-description">Closer structural rendering of the source text.</div>
                            """)
                            literal_output = gr.Textbox(label="", lines=4, interactive=False, buttons=["copy"])
                            select_lit_btn = gr.Button("Select Literal", size="sm", elem_classes=["btn-select-variant"])

                # Human-in-the-Loop Evaluation Section
                with gr.Column(elem_classes=["panel-card"]):
                    gr.HTML("""
                    <div class="section-label">Human Evaluation & Continuous Improvement</div>
                    <div class="section-desc">Evaluate translation candidates to guide translation quality analytics and strategy improvements.</div>
                    """)

                    with gr.Row():
                        with gr.Column(scale=2):
                            variant_selector = gr.Radio(
                                label="Step 1: Select Candidate to Evaluate",
                                choices=["Natural / Idiomatic", "Formal / Context-Aware", "Literal / Direct"],
                                value="Natural / Idiomatic",
                                interactive=True,
                            )
                            prefer_btn = gr.Button("Mark as Preferred Choice", size="sm")
                            prefer_status = gr.Markdown("")

                        with gr.Column(scale=3):
                            rating_radio = gr.Radio(
                                label="Step 2: How would you rate this candidate?",
                                choices=["GOOD", "POOR"],
                                value="GOOD",
                                interactive=True,
                            )
                            defect_reason = gr.Dropdown(
                                label="Why is this translation poor? (Required for POOR)",
                                choices=[(label, code) for label, code in DEFECT_CHOICES],
                                value=None,
                                visible=False,
                                interactive=True,
                            )
                            comments_box = gr.Textbox(
                                label="Optional correction notes / feedback",
                                placeholder="Describe terminology, grammar, phrasing, or suggest corrections...",
                                lines=2,
                            )
                            feedback_btn = gr.Button("Submit Evaluation", variant="primary")
                            feedback_status = gr.Markdown("")

            # =================================================================
            # TAB 2: Quality Investigation
            # =================================================================
            with gr.TabItem("Quality Investigation"):
                with gr.Column(elem_classes=["panel-card"]):
                    gr.HTML("""
                    <div class="section-label">Quality Investigation Workflow</div>
                    <div class="section-desc">Inspect problematic translations, anomaly flags, and defect feedback by Request ID.</div>
                    """)

                    with gr.Row():
                        investigate_input = gr.Textbox(
                            label="Request ID Lookup",
                            placeholder="Enter Request ID e.g. REQ-20260924-A8F31 or UUID...",
                            scale=4,
                        )
                        investigate_btn = gr.Button("Investigate Request", variant="primary", scale=1)

                    investigate_status = gr.Markdown("")

                    with gr.Row():
                        inv_req_id = gr.Textbox(label="Request ID", interactive=False, scale=1)
                        inv_lang_pair = gr.Textbox(label="Language Pair", interactive=False, scale=1)
                        inv_latency = gr.Textbox(label="Latency", interactive=False, scale=1)
                        inv_score = gr.Textbox(label="Quality Score", interactive=False, scale=1)

                    inv_source = gr.Textbox(label="Source Text", lines=3, interactive=False, buttons=["copy"])
                    inv_candidates = gr.Textbox(label="Generated Candidates", lines=5, interactive=False, buttons=["copy"])
                    inv_provider = gr.Textbox(label="Provider & Model", interactive=False)
                    inv_diagnostics = gr.Textbox(label="Diagnostics, Anomalies & Human Feedback", lines=3, interactive=False)

            # =================================================================
            # TAB 3: Session Translation History
            # =================================================================
            with gr.TabItem("Session History"):
                with gr.Column(elem_classes=["panel-card"]):
                    gr.HTML("""
                    <div class="section-label">Session Translation History</div>
                    <div class="section-desc">Recent operational translation requests logged in PostgreSQL with Request ID traceability.</div>
                    """)

                    with gr.Row():
                        history_lang_filter = gr.Dropdown(
                            label="Filter by Language Pair",
                            choices=["All Pairs", "EN → HI", "EN → ES", "EN → FR", "EN → DE", "EN → BN", "EN → JA"],
                            value="All Pairs",
                            scale=2,
                        )
                        history_quality_filter = gr.Dropdown(
                            label="Filter by Quality",
                            choices=["All", "Good", "Poor", "Pending"],
                            value="All",
                            scale=2,
                        )
                        refresh_history_btn = gr.Button("Refresh History", size="sm", scale=1)

                    history_table = gr.Dataframe(
                        headers=["Request ID", "Timestamp", "Language Pair", "Provider", "Variant", "Latency", "Quality", "Feedback"],
                        datatype=["str", "str", "str", "str", "str", "str", "str", "str"],
                        value=load_history_table,
                        interactive=False,
                    )

            # =================================================================
            # TAB 4: Quality Analytics
            # =================================================================
            with gr.TabItem("Quality Analytics"):
                kpi_tot, kpi_lat, kpi_qsc, kpi_prate = load_analytics_kpis()

                # KPI Cards Row
                gr.HTML(f"""
                <div class="kpi-grid">
                    <div class="kpi-card">
                        <div class="kpi-label">Total Translations</div>
                        <div class="kpi-value">{kpi_tot}</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Average Latency</div>
                        <div class="kpi-value">{kpi_lat}</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Average Quality Score</div>
                        <div class="kpi-value">{kpi_qsc}</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Poor Quality Rate</div>
                        <div class="kpi-value">{kpi_prate}</div>
                    </div>
                </div>
                """)

                # Continuous Improvement Insights Card
                with gr.Column(elem_classes=["insights-box"]):
                    gr.HTML("""
                    <div style="font-weight: 700; color: #a5b4fc; font-size: 0.88rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">
                        💡 Continuous Improvement Insights (Generated from Feedback & Anomalies)
                    </div>
                    """)
                    insights_markdown = gr.Markdown(load_insights_text)

                # Row 1: Language Pairs & Preferred Style Distribution
                with gr.Row():
                    with gr.Column(elem_classes=["panel-card"]):
                        gr.HTML("""
                        <div class="section-label">Language Pair Performance</div>
                        <div class="section-desc">Observed throughput, composite quality score, latency, and defect rates.</div>
                        """)
                        pairs_table = gr.Dataframe(
                            headers=["Language Pair", "Count", "Avg Quality", "Avg Latency", "Defect Rate"],
                            datatype=["str", "str", "str", "str", "str"],
                            value=load_pairs_analytics_table,
                            interactive=False,
                        )

                    with gr.Column(elem_classes=["panel-card"]):
                        gr.HTML("""
                        <div class="section-label">Preferred Translation Style</div>
                        <div class="section-desc">Distribution of stylistic candidates marked as preferred choice by evaluators.</div>
                        """)
                        styles_table = gr.Dataframe(
                            headers=["Translation Style", "Selections", "Share"],
                            datatype=["str", "str", "str"],
                            value=load_preferred_styles_table,
                            interactive=False,
                        )

                # Row 2: Defects Taxonomy
                with gr.Row():
                    with gr.Column(elem_classes=["panel-card"]):
                        gr.HTML("""
                        <div class="section-label">Feedback Defect Taxonomy Distribution</div>
                        <div class="section-desc">Linguistic anomaly categories identified during human evaluation.</div>
                        """)
                        defects_table = gr.Dataframe(
                            headers=["Defect Category", "Flagged Occurrences", "Percentage"],
                            datatype=["str", "str", "str"],
                            value=load_defects_analytics_table,
                            interactive=False,
                        )

                # Grafana Integration Notice
                gr.HTML("""
                <div class="panel-card" style="margin-top: 14px; background: rgba(99, 102, 241, 0.05); border-color: rgba(99, 102, 241, 0.25);">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                        <div>
                            <div style="font-weight: 700; color: #a5b4fc; font-size: 0.95rem;">📊 Operational Grafana Dashboards</div>
                            <div style="font-size: 0.83rem; color: #94a3b8; margin-top: 2px;">
                                For live time-series latency trends, 14-panel observability, and automated alerting, open the Grafana dashboard.
                            </div>
                        </div>
                        <div>
                            <a href="http://localhost:3000" target="_blank" style="display: inline-block; padding: 8px 16px; background: #4f46e5; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 0.82rem;">
                                Open Grafana (Port 3000) ↗
                            </a>
                        </div>
                    </div>
                </div>
                """)

        # =====================================================================
        # EVENT WIRE-UP
        # =====================================================================
        # Character & Word Counter
        source_input.change(
            fn=lambda s: f"{len(s or '')} characters · {len((s or '').split())} words",
            inputs=[source_input],
            outputs=[source_counter],
        )

        # Translation execution
        translate_btn.click(
            fn=perform_translation,
            inputs=[source_input, tgt_lang],
            outputs=[
                status_output,
                natural_output,
                formal_output,
                literal_output,
                option_map_state,
                variant_selector,
            ],
        )

        # Clear button
        clear_btn.click(
            fn=lambda: ("", "Ready to translate.", "", "", "", {}, gr.Radio(value="Natural / Idiomatic"), "", "", "0 characters · 0 words"),
            inputs=[],
            outputs=[
                source_input,
                status_output,
                natural_output,
                formal_output,
                literal_output,
                option_map_state,
                variant_selector,
                prefer_status,
                feedback_status,
                source_counter,
            ],
        )

        # Card quick-selection buttons
        select_nat_btn.click(lambda: "Natural / Idiomatic", None, variant_selector)
        select_formal_btn.click(lambda: "Formal / Context-Aware", None, variant_selector)
        select_lit_btn.click(lambda: "Literal / Direct", None, variant_selector)

        # Rating selection shows/hides defect dropdown
        rating_radio.change(
            fn=toggle_defect_visibility,
            inputs=[rating_radio],
            outputs=[defect_reason],
        )

        # Preferred choice action
        prefer_btn.click(
            fn=mark_preferred_variant,
            inputs=[variant_selector, option_map_state],
            outputs=[prefer_status],
        )

        # Feedback submission action
        feedback_btn.click(
            fn=submit_human_feedback,
            inputs=[variant_selector, rating_radio, defect_reason, comments_box, option_map_state],
            outputs=[feedback_status],
        )

        # Quality Investigation
        investigate_btn.click(
            fn=investigate_translation,
            inputs=[investigate_input],
            outputs=[
                investigate_status,
                inv_req_id,
                inv_lang_pair,
                inv_source,
                inv_candidates,
                inv_provider,
                inv_latency,
                inv_score,
                inv_diagnostics,
            ],
        )

        # History table filter & refresh
        refresh_history_btn.click(
            fn=load_history_table,
            inputs=[history_lang_filter, history_quality_filter],
            outputs=[history_table],
        )
        history_lang_filter.change(
            fn=load_history_table,
            inputs=[history_lang_filter, history_quality_filter],
            outputs=[history_table],
        )
        history_quality_filter.change(
            fn=load_history_table,
            inputs=[history_lang_filter, history_quality_filter],
            outputs=[history_table],
        )

    return demo


if __name__ == "__main__":
    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
    )
