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
    "TOO_LITERAL",
    "WRONG_CONTEXT",
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
            translation = Translation(
                id=dto.request_id,
                provider=dto.provider,
                source_text=dto.source_text,
                source_language=dto.source_language,
                target_language=dto.target_language,
                translation_time_ms=dto.translation_time_ms,
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
                    user_selected=opt_dto.user_selected,
                    created_at=datetime.now(timezone.utc),
                )
                sess.add(option)

            logger.info(
                f"Saved translation {translation.id} ({translation.provider}, "
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
        """Marks a candidate style option as selected by the user."""
        opt_uuid = UUID(str(option_id))

        def _execute(sess: Session) -> Optional[TranslationOption]:
            option = sess.get(TranslationOption, opt_uuid)
            if option:
                option.user_selected = True
                logger.info(f"Option {opt_uuid} marked as user_selected.")
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
                .options(joinedload(Translation.options))
                .where(Translation.id == trans_uuid)
            )
            return sess.execute(stmt).unique().scalar_one_or_none()

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
        """Retrieves recent translations ordered by created_at DESC with eager-loaded options."""
        def _execute(sess: Session) -> List[Translation]:
            stmt = (
                select(Translation)
                .options(joinedload(Translation.options))
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


# Default singleton instance
default_repository = TranslationRepository()
