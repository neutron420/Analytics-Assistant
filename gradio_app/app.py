"""
Gradio Web Application
Translation Quality Analytics & Continuous Improvement Platform

Provides interactive human-in-the-loop translation interface, multi-style rendering,
qualitative feedback collection, and live session history.
"""

import logging
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import gradio as gr

from src.config import config
from src.database.connection import check_db_health
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

DEFECT_REASONS = [
    ("Incorrect Meaning / Semantic Error", "INCORRECT_MEANING"),
    ("Grammar / Syntactic Defect", "GRAMMAR"),
    ("Too Literal / Unnatural Calque", "TOO_LITERAL"),
    ("Wrong Context / Register / Tone", "WRONG_CONTEXT"),
    ("Other / Miscellaneous Defect", "OTHER"),
]

CUSTOM_CSS = """
/* Premium Dark Interface Styling */
:root {
    --primary-color: #6366f1;
    --primary-hover: #4f46e5;
    --surface-dark: #0f172a;
    --card-bg: #1e293b;
    --border-color: #334155;
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
}

body, .gradio-container {
    background-color: var(--surface-dark) !important;
    color: var(--text-main) !important;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif !important;
}

.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    border-radius: 9999px;
    font-size: 0.82rem;
    font-weight: 600;
    background: rgba(99, 102, 241, 0.12);
    border: 1px solid rgba(99, 102, 241, 0.3);
    color: #a5b4fc;
}

.variant-card {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 12px;
    transition: all 0.2s ease-in-out;
}

.variant-card:hover {
    border-color: var(--primary-color);
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.15);
}

.latency-tag {
    font-size: 0.78rem;
    color: #38bdf8;
    font-family: monospace;
}
"""


def perform_translation(
    source_text: str,
    target_lang_label: str
) -> Tuple[str, str, str, str, Dict[str, str], gr.Radio]:
    """
    Executes translation via provider-agnostic TranslationService,
    persists result in PostgreSQL, and formats candidate style cards.
    """
    clean_text = (source_text or "").strip()
    if not clean_text:
        return (
            "Please enter source text to translate.",
            "",
            "",
            "",
            {},
            gr.Radio(choices=[], value=None),
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
            logger.warning(f"Background DB persistence warning: {db_err}")

        # 3. Parse options
        literal_text = ""
        natural_text = ""
        formal_text = ""
        option_map: Dict[str, str] = {}

        radio_choices = []
        for opt in result_dto.options:
            style = opt.style_option
            option_map[style] = str(opt.option_id)
            label = f"{style}: {opt.translated_text[:35]}..." if len(opt.translated_text) > 35 else f"{style}: {opt.translated_text}"
            radio_choices.append((label, style))

            if style == "LITERAL":
                literal_text = opt.translated_text
            elif style == "NATURAL":
                natural_text = opt.translated_text
            elif style == "FORMAL":
                formal_text = opt.translated_text

        status_msg = (
            f"✅ **Translation Completed** in `{result_dto.translation_time_ms} ms` "
            f"using provider `{result_dto.provider}` ({target_code.upper()})."
        )

        return (
            status_msg,
            natural_text,
            formal_text,
            literal_text,
            option_map,
            gr.Radio(choices=radio_choices, value=radio_choices[0][1] if radio_choices else None),
        )

    except Exception as exc:
        logger.error(f"Translation execution failed: {exc}", exc_info=True)
        return (
            f"❌ **Translation Error**: {str(exc)}",
            "",
            "",
            "",
            {},
            gr.Radio(choices=[], value=None),
        )


def submit_human_feedback(
    selected_style: Optional[str],
    rating: str,
    reason_code: Optional[str],
    comments: str,
    option_map: Dict[str, str],
) -> str:
    """Submits human quality evaluation to FeedbackService."""
    if not selected_style or selected_style not in option_map:
        return "⚠️ Please select which translation candidate option you are evaluating."

    option_id_str = option_map[selected_style]
    clean_rating = "GOOD" if "GOOD" in rating.upper() else "POOR"

    if clean_rating == "POOR" and not reason_code:
        return "⚠️ Please choose a specific defect reason when rating a translation as POOR."

    try:
        dto = FeedbackSubmissionDTO(
            option_id=UUID(option_id_str),
            rating=clean_rating,
            reason=reason_code if clean_rating == "POOR" else None,
            comments=comments.strip() if comments else None,
        )
        res = default_feedback_service.record_feedback(dto)
        return f"🎉 **Feedback Recorded!** {res.message} (Option: `{selected_style}` | Rating: `{clean_rating}`)"
    except Exception as exc:
        logger.error(f"Feedback submission error: {exc}", exc_info=True)
        return f"❌ **Error Submitting Feedback**: {str(exc)}"


def mark_preferred_variant(selected_style: Optional[str], option_map: Dict[str, str]) -> str:
    """Marks chosen candidate style as preferred in the database."""
    if not selected_style or selected_style not in option_map:
        return "⚠️ Please select a variant option first."

    option_id_str = option_map[selected_style]
    try:
        success = default_feedback_service.select_preferred_option(UUID(option_id_str))
        if success:
            return f"⭐ Option **{selected_style}** marked as preferred variant!"
        return "⚠️ Could not update preferred variant in database."
    except Exception as exc:
        return f"❌ Error: {str(exc)}"


def load_history_table() -> List[List[str]]:
    """Loads recent translations from the database for the history tab."""
    try:
        recent = default_repository.get_recent_translations(limit=12)
        rows = []
        for r in recent:
            ts = r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "N/A"
            rows.append([
                ts,
                f"{r.source_language} ➔ {r.target_language}",
                r.source_text[:50] + ("..." if len(r.source_text) > 50 else ""),
                r.provider,
                f"{r.translation_time_ms} ms",
                str(len(r.options)),
            ])
        return rows
    except Exception as exc:
        logger.warning(f"Error loading history: {exc}")
        return [["Error", "N/A", str(exc), "N/A", "0 ms", "0"]]


def create_app() -> gr.Blocks:
    """Constructs the Gradio Blocks UI application."""
    db_health = check_db_health()
    db_status_label = "🟢 Connected" if db_health.get("status") == "healthy" else "🔴 Offline"

    with gr.Blocks(title="Translation Quality Analytics Platform") as demo:
        # Header & Status Badges
        with gr.Row():
            with gr.Column(scale=8):
                gr.Markdown(
                    "# 🌐 Translation Quality Analytics & Continuous Improvement Platform\n"
                    "Multi-style high-performance translation engine with human-in-the-loop evaluation and PySpark batch analytics."
                )
            with gr.Column(scale=4):
                gr.Markdown(
                    f"<div style='text-align: right; padding-top: 10px;'>"
                    f"<span class='status-badge'>Provider: <b>{config.translation_provider.upper()}</b></span> &nbsp; "
                    f"<span class='status-badge'>DB: <b>{db_status_label}</b></span>"
                    f"</div>"
                )

        # In-memory session state for option mapping {style: uuid_string}
        option_map_state = gr.State({})

        with gr.Tabs():
            # ==========================================
            # TAB 1: Translate & Evaluate
            # ==========================================
            with gr.TabItem("🚀 Translate & Evaluate"):
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
                    label="Input Source Text (English)",
                    placeholder="Enter sentence or paragraph to translate (e.g. 'The sudden change in economic policy created widespread uncertainty among small businesses.')...",
                    lines=4,
                    max_lines=8,
                )

                with gr.Row():
                    translate_btn = gr.Button("⚡ Translate Now", variant="primary", scale=3)
                    clear_btn = gr.Button("🧹 Clear", variant="secondary", scale=1)

                status_output = gr.Markdown("Ready to translate.")

                gr.Markdown("### 🎯 Generated Translation Style Variants")
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### 🌿 Natural / Idiomatic (Recommended)")
                        natural_output = gr.Textbox(label="", lines=3, interactive=False)
                    with gr.Column():
                        gr.Markdown("#### 👔 Formal / Context-Aware")
                        formal_output = gr.Textbox(label="", lines=3, interactive=False)
                    with gr.Column():
                        gr.Markdown("#### 📖 Literal / Direct")
                        literal_output = gr.Textbox(label="", lines=3, interactive=False)

                gr.Markdown("---")
                gr.Markdown("### ✍️ Human-in-the-Loop Quality Feedback")

                with gr.Row():
                    with gr.Column(scale=2):
                        variant_selector = gr.Radio(
                            label="1. Select Candidate Variant to Rate / Prefer",
                            choices=[],
                            interactive=True,
                        )
                        prefer_btn = gr.Button("⭐ Mark as Preferred Choice", size="sm")
                        prefer_status = gr.Markdown("")

                    with gr.Column(scale=3):
                        rating_radio = gr.Radio(
                            label="2. Quality Rating",
                            choices=["👍 GOOD (Accurate & Natural)", "👎 POOR (Contains Defects)"],
                            value="👍 GOOD (Accurate & Natural)",
                            interactive=True,
                        )
                        defect_reason = gr.Dropdown(
                            label="3. Defect Reason (Required if POOR)",
                            choices=[(label, code) for label, code in DEFECT_REASONS],
                            value=None,
                            interactive=True,
                        )
                        comments_box = gr.Textbox(
                            label="4. Corrections / Linguistic Notes (Optional)",
                            placeholder="Add remarks on unnatural phrasing, terminology, or register...",
                            lines=2,
                        )
                        feedback_btn = gr.Button("📩 Submit Quality Feedback", variant="secondary")
                        feedback_status = gr.Markdown("")

            # ==========================================
            # TAB 2: Session Translation History
            # ==========================================
            with gr.TabItem("📜 Session Translation History"):
                gr.Markdown("### 🕒 Real-Time Audit Log (PostgreSQL System of Record)")
                with gr.Row():
                    refresh_history_btn = gr.Button("🔄 Refresh History", size="sm")

                history_table = gr.Dataframe(
                    headers=["Timestamp (UTC)", "Pair", "Source Snippet", "Provider", "Latency", "Options"],
                    datatype=["str", "str", "str", "str", "str", "str"],
                    value=load_history_table,
                    interactive=False,
                )

            # ==========================================
            # TAB 3: Architecture & Analytics Mart
            # ==========================================
            with gr.TabItem("📊 Quality Analytics & Monitoring"):
                gr.Markdown(
                    "### 📈 Continuous Improvement Pipeline\n\n"
                    "- **PySpark Analytical Mart**: Ingests `translations` and `feedback` daily, computing length ratios, "
                    "Levenshtein divergence, and human downvote rates.\n"
                    "- **Grafana Observability**: Pre-built dashboard monitoring latency percentiles, error rates, "
                    "and language pair quality scores.\n\n"
                    "👉 **Grafana Dashboard URL**: [http://localhost:3000](http://localhost:3000) *(Default user: `admin` / `admin`)*\n"
                    "👉 **PostgreSQL Data Mart**: Port `5435`, Database `translation_analytics`."
                )

        # ==========================================
        # Event Wire-Up
        # ==========================================
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

        clear_btn.click(
            fn=lambda: ("", "", "", "", "", {}, gr.Radio(choices=[], value=None), ""),
            inputs=[],
            outputs=[
                source_input,
                status_output,
                natural_output,
                formal_output,
                literal_output,
                option_map_state,
                variant_selector,
                feedback_status,
            ],
        )

        prefer_btn.click(
            fn=mark_preferred_variant,
            inputs=[variant_selector, option_map_state],
            outputs=[prefer_status],
        )

        feedback_btn.click(
            fn=submit_human_feedback,
            inputs=[variant_selector, rating_radio, defect_reason, comments_box, option_map_state],
            outputs=[feedback_status],
        )

        refresh_history_btn.click(
            fn=load_history_table,
            inputs=[],
            outputs=[history_table],
        )

    return demo


# Global application instance
app = create_app()

if __name__ == "__main__":
    app.launch(
        server_name=config.gradio_server_name,
        server_port=config.gradio_server_port,
        theme=gr.themes.Soft(),
        css=CUSTOM_CSS,
        share=False,
    )
