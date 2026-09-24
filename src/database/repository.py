"""
Database Repository
Translation Quality Analytics & Continuous Improvement Platform

Provides data access methods for translations, style options, human feedback,
and analytical reporting aggregates.
"""

import logging
from datetime import date, datetime, timezone
from typing import List, Optional, Union
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from src.database.connection import get_db_session
from src.database.models import (
    AnalyticsAnomaly,
    AnalyticsDailyMetric,
    Feedback,
    Translation,
    TranslationOption,
)
from src.translation.models import TranslationResultDTO

logger = logging.getLogger(__name__)

ALLOWED_RATINGS = {"GOOD", "POOR"}
ALLOWED_REASONS = {
    "INCORRECT_MEANING",
    "GRAMMAR",
    "GRAMMAR_ISSUE",
    "TOO_LITERAL",
    "WRONG_CONTEXT",
    "UNNATURAL_PHRASING",
    "TERMINOLOGY_ISSUE",
    "OTHER",
}


class TranslationRepository:
    """Encapsulates transactional CRUD operations for translation workflow entities."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or get_db_session

    def save_translation(
        self,
        dto: TranslationResultDTO,
        client_ip: Optional[str] = None,
        session: Optional[Session] = None
    ) -> Translation:
        """
        Persists a completed translation request and all generated candidate style options.
        
        Args:
            dto: Completed translation result DTO containing telemetry and options.
            client_ip: Optional client IP address.
            session: Optional existing active SQLAlchemy session.
        
        Returns:
            The saved Translation ORM instance.
        """
        def _execute(sess: Session) -> Translation:
            anomaly_reasons_str = ",".join(dto.anomaly_reasons) if dto.anomaly_reasons else None
            translation = Translation(
                id=dto.request_id,
                request_id=dto.human_request_id,
                provider=dto.provider,
                model=dto.model,
                source_text=dto.source_text,
                source_language=dto.source_language,
                target_language=dto.target_language,
                translation_time_ms=dto.translation_time_ms,
                quality_score=dto.quality_score,
                anomaly_flag=dto.anomaly_flag,
                anomaly_reasons=anomaly_reasons_str,
                status=dto.status,
                client_ip=client_ip,
                created_at=datetime.now(timezone.utc),
            )
            sess.add(translation)
            sess.flush()  # Ensures translation.id is available

            for opt_dto in dto.options:
                option = TranslationOption(
                    id=opt_dto.option_id,
                    translation_id=translation.id,
                    style_option=opt_dto.style_option,
                    translated_text=opt_dto.translated_text,
                    confidence_score=opt_dto.confidence_score,
                    text_length=opt_dto.text_length or len((opt_dto.translated_text or "").strip()),
                    user_selected=opt_dto.user_selected,
                    created_at=datetime.now(timezone.utc),
                )
                sess.add(option)

            logger.info(
                f"Saved translation {translation.request_id} ({translation.provider}, "
                f"{translation.source_language}->{translation.target_language}) with {len(dto.options)} options."
            )
            return translation

        if session is not None:
            return _execute(session)
        with self._session_factory() as sess:
            return _execute(sess)

    def record_feedback(
        self,
        option_id: Union[UUID, str],
        rating: str,
        reason: Optional[str] = None,
        comments: Optional[str] = None,
        session: Optional[Session] = None
    ) -> Feedback:
        """
        Persists human-in-the-loop qualitative feedback on a translation candidate.
        
        Args:
            option_id: UUID of the TranslationOption being rated.
            rating: Either 'GOOD' or 'POOR'.
            reason: Defect taxonomy category if rating is 'POOR'.
            comments: Free-form user feedback.
            session: Optional existing active SQLAlchemy session.
        
        Returns:
            The created Feedback ORM instance.
        """
        opt_uuid = UUID(str(option_id))
        normalized_rating = rating.strip().upper()
        if normalized_rating not in ALLOWED_RATINGS:
            raise ValueError(f"Invalid rating '{rating}'. Allowed: {ALLOWED_RATINGS}")

        normalized_reason = reason.strip().upper() if reason else None
        if normalized_reason == "GRAMMAR":
            normalized_reason = "GRAMMAR_ISSUE"

        if normalized_rating == "POOR" and not normalized_reason:
            raise ValueError("Defect reason is required for POOR feedback rating.")

        if normalized_reason and normalized_reason not in ALLOWED_REASONS:
            raise ValueError(f"Invalid reason '{reason}'. Allowed: {ALLOWED_REASONS}")

        def _execute(sess: Session) -> Feedback:
            feedback = Feedback(
                option_id=opt_uuid,
                rating=normalized_rating,
                reason=normalized_reason,
                comments=comments.strip() if comments else None,
                created_at=datetime.now(timezone.utc),
            )
            sess.add(feedback)

            # When poor feedback is recorded, update translation anomaly_flag to reflect quality degradation
            option = sess.get(TranslationOption, opt_uuid)
            if option and normalized_rating == "POOR":
                translation = sess.get(Translation, option.translation_id)
                if translation:
                    translation.anomaly_flag = True
                    current_reasons = translation.anomaly_reasons.split(",") if translation.anomaly_reasons else []
                    if "QUALITY_DEGRADATION" not in current_reasons:
                        current_reasons.append("QUALITY_DEGRADATION")
                        translation.anomaly_reasons = ",".join(current_reasons)
                    if translation.quality_score is not None:
                        translation.quality_score = max(20.0, round(translation.quality_score - 28.0, 1))

            logger.info(f"Recorded feedback for option {opt_uuid}: rating={normalized_rating}, reason={normalized_reason}")
            return feedback

        if session is not None:
            return _execute(session)
        with self._session_factory() as sess:
            return _execute(sess)

    def mark_option_selected(
        self,
        option_id: Union[UUID, str],
        session: Optional[Session] = None
    ) -> Optional[TranslationOption]:
        """Marks a candidate style option as preferred / selected by the user."""
        opt_uuid = UUID(str(option_id))

        def _execute(sess: Session) -> Optional[TranslationOption]:
            option = sess.get(TranslationOption, opt_uuid)
            if option:
                siblings = sess.execute(
                    select(TranslationOption).where(TranslationOption.translation_id == option.translation_id)
                ).scalars().all()
                for sib in siblings:
                    sib.user_selected = (sib.id == option.id)
                logger.info(f"Option {opt_uuid} marked as user_selected (preferred).")
            return option

        if session is not None:
            return _execute(session)
        with self._session_factory() as sess:
            return _execute(sess)

    def get_translation_by_id(
        self,
        translation_id: Union[UUID, str],
        session: Optional[Session] = None
    ) -> Optional[Translation]:
        """Retrieves a translation by its UUID, including all candidate options."""
        trans_uuid = UUID(str(translation_id))

        def _execute(sess: Session) -> Optional[Translation]:
            stmt = (
                select(Translation)
                .options(joinedload(Translation.options).joinedload(TranslationOption.feedback))
                .where(Translation.id == trans_uuid)
            )
            return sess.execute(stmt).unique().scalar_one_or_none()

        if session is not None:
            return _execute(session)
        with self._session_factory() as sess:
            return _execute(sess)

    def get_translation_by_request_id(
        self,
        request_id: str,
        session: Optional[Session] = None
    ) -> Optional[Translation]:
        """
        Retrieves a translation and its options/feedback by human-readable request_id
        (e.g., 'REQ-20260924-A8F31') or internal UUID string.
        """
        req_clean = request_id.strip()

        def _execute(sess: Session) -> Optional[Translation]:
            stmt = (
                select(Translation)
                .options(joinedload(Translation.options).joinedload(TranslationOption.feedback))
            )
            # Try searching by human request_id first
            res = sess.execute(stmt.where(Translation.request_id == req_clean)).unique().scalar_one_or_none()
            if res:
                return res
            # Fallback: try UUID if formatted as UUID
            try:
                trans_uuid = UUID(req_clean)
                return sess.execute(stmt.where(Translation.id == trans_uuid)).unique().scalar_one_or_none()
            except ValueError:
                return None

        if session is not None:
            return _execute(session)
        with self._session_factory() as sess:
            return _execute(sess)

    def get_recent_translations(
        self,
        limit: int = 10,
        offset: int = 0,
        session: Optional[Session] = None
    ) -> List[Translation]:
        """Retrieves recent translations ordered by created_at DESC with eager-loaded options and feedback."""
        def _execute(sess: Session) -> List[Translation]:
            stmt = (
                select(Translation)
                .options(joinedload(Translation.options).joinedload(TranslationOption.feedback))
                .order_by(desc(Translation.created_at))
                .limit(limit)
                .offset(offset)
            )
            return list(sess.execute(stmt).unique().scalars().all())

        if session is not None:
            return _execute(session)
        with self._session_factory() as sess:
            return _execute(sess)

    def get_daily_metrics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        provider: Optional[str] = None,
        session: Optional[Session] = None
    ) -> List[AnalyticsDailyMetric]:
        """Retrieves analytics metrics sliced by optional date range and provider."""
        def _execute(sess: Session) -> List[AnalyticsDailyMetric]:
            stmt = select(AnalyticsDailyMetric)
            if start_date:
                stmt = stmt.where(AnalyticsDailyMetric.metric_date >= start_date)
            if end_date:
                stmt = stmt.where(AnalyticsDailyMetric.metric_date <= end_date)
            if provider:
                stmt = stmt.where(AnalyticsDailyMetric.provider == provider)
            stmt = stmt.order_by(desc(AnalyticsDailyMetric.metric_date))
            return list(sess.execute(stmt).scalars().all())

        if session is not None:
            return _execute(session)
        with self._session_factory() as sess:
            return _execute(sess)

    def get_live_analytics_summary(self, session: Optional[Session] = None) -> dict:
        """
        Computes real-time live operational analytics directly from PostgreSQL
        for the Gradio Analytics dashboard and Continuous Improvement insights.
        """
        def _execute(sess: Session) -> dict:
            translations = sess.execute(
                select(Translation).options(joinedload(Translation.options))
            ).unique().scalars().all()

            total_translations = len(translations)
            if total_translations == 0:
                return {
                    "total_translations": 0,
                    "avg_latency_s": 0.0,
                    "poor_feedback_rate": 0.0,
                    "avg_quality_score": 0.0,
                    "total_feedbacks": 0,
                    "poor_feedback_count": 0,
                    "good_feedback_count": 0,
                    "language_pairs": [],
                    "feedback_reasons": {},
                    "style_preferences": {},
                    "anomalies_count": 0,
                    "recent_anomalies": [],
                    "insights": ["Not enough feedback data to generate an insight."]
                }

            total_latency_ms = sum(t.translation_time_ms for t in translations)
            avg_latency_s = round((total_latency_ms / total_translations) / 1000.0, 2)

            quality_scores = [t.quality_score for t in translations if t.quality_score is not None]
            avg_quality = round(sum(quality_scores) / len(quality_scores), 1) if quality_scores else 88.0

            # Gather options & query all feedbacks directly
            all_feedbacks = sess.execute(select(Feedback)).scalars().all()
            anomalies = [t for t in translations if t.anomaly_flag]

            good_count = sum(1 for f in all_feedbacks if f.rating == "GOOD")
            poor_count = sum(1 for f in all_feedbacks if f.rating == "POOR")
            total_fb = len(all_feedbacks)
            poor_rate = round((poor_count / total_fb * 100.0), 1) if total_fb > 0 else 0.0

            # Defect reasons distribution
            reason_counts = {}
            for f in all_feedbacks:
                if f.rating == "POOR" and f.reason:
                    reason_counts[f.reason] = reason_counts.get(f.reason, 0) + 1

            feedback_reasons = {}
            for r, count in reason_counts.items():
                pct = round((count / poor_count * 100.0), 1) if poor_count > 0 else 0.0
                feedback_reasons[r] = {"count": count, "percentage": pct}

            # Style preference distribution
            preferred_counts = {"NATURAL": 0, "FORMAL": 0, "LITERAL": 0}
            opt_to_pair = {}
            for t in translations:
                pair_name = f"{t.source_language.upper()} \u2192 {t.target_language.upper()}"
                for opt in t.options:
                    opt_to_pair[opt.id] = pair_name
                    if opt.user_selected:
                        preferred_counts[opt.style_option] = preferred_counts.get(opt.style_option, 0) + 1

            total_pref = sum(preferred_counts.values())
            style_preferences = {}
            for style, count in preferred_counts.items():
                pct = round((count / total_pref * 100.0), 1) if total_pref > 0 else 0.0
                style_preferences[style] = {"count": count, "percentage": pct}

            # Language pair aggregations
            pairs_dict = {}
            for t in translations:
                pair_name = f"{t.source_language.upper()} \u2192 {t.target_language.upper()}"
                if pair_name not in pairs_dict:
                    pairs_dict[pair_name] = {
                        "count": 0,
                        "total_latency_ms": 0,
                        "quality_scores": [],
                        "poor_feedbacks": 0,
                        "total_feedbacks": 0,
                    }
                pairs_dict[pair_name]["count"] += 1
                pairs_dict[pair_name]["total_latency_ms"] += t.translation_time_ms
                if t.quality_score is not None:
                    pairs_dict[pair_name]["quality_scores"].append(t.quality_score)

            for f in all_feedbacks:
                pair = opt_to_pair.get(f.option_id)
                if pair and pair in pairs_dict:
                    pairs_dict[pair]["total_feedbacks"] += 1
                    if f.rating == "POOR":
                        pairs_dict[pair]["poor_feedbacks"] += 1

            language_pairs = []
            for pair, data in pairs_dict.items():
                cnt = data["count"]
                avg_lat = round((data["total_latency_ms"] / cnt) / 1000.0, 2)
                qs = data["quality_scores"]
                avg_q = round(sum(qs) / len(qs), 1) if qs else 88.0
                tfb = data["total_feedbacks"]
                p_rate = round((data["poor_feedbacks"] / tfb * 100.0), 1) if tfb > 0 else 0.0
                language_pairs.append({
                    "language_pair": pair,
                    "translation_count": cnt,
                    "avg_latency_s": avg_lat,
                    "observed_quality_rate": f"{100.0 - p_rate:.1f}%",
                    "poor_feedback_rate": f"{p_rate:.1f}%",
                    "avg_quality_score": avg_q,
                })

            # Automated Continuous Improvement Insights
            insights = []
            if total_fb >= 2 and poor_count > 0:
                top_reason = max(reason_counts.items(), key=lambda x: x[1])[0]
                insights.append(f"'{top_reason.replace('_', ' ').title()}' is currently the most frequently reported defect reason ({feedback_reasons[top_reason]['percentage']}% of negative feedback).")
            if total_pref >= 2:
                top_style = max(preferred_counts.items(), key=lambda x: x[1])[0]
                insights.append(f"'{top_style.title()}' variant demonstrates the highest user selection rate ({style_preferences[top_style]['percentage']}% of preferred choices).")
            if len(anomalies) > 0:
                insights.append(f"Operational anomaly detection flagged {len(anomalies)} translation requests requiring review.")
            if not insights:
                insights.append("Not enough feedback data to generate an insight.")

            return {
                "total_translations": total_translations,
                "avg_latency_s": avg_latency_s,
                "poor_feedback_rate": poor_rate,
                "avg_quality_score": avg_quality,
                "total_feedbacks": total_fb,
                "poor_feedback_count": poor_count,
                "good_feedback_count": good_count,
                "language_pairs": language_pairs,
                "feedback_reasons": feedback_reasons,
                "style_preferences": style_preferences,
                "anomalies_count": len(anomalies),
                "recent_anomalies": [
                    {
                        "request_id": a.request_id or str(a.id),
                        "pair": f"{a.source_language.upper()} \u2192 {a.target_language.upper()}",
                        "reasons": a.anomaly_reasons or "UNKNOWN",
                        "latency_s": round(a.translation_time_ms / 1000.0, 2),
                        "quality_score": a.quality_score,
                    }
                    for a in anomalies[:5]
                ],
                "insights": insights,
            }

        if session is not None:
            return _execute(session)
        with self._session_factory() as sess:
            return _execute(sess)


# Default singleton instance
default_repository = TranslationRepository()

