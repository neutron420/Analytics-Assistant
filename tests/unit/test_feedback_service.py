"""
Unit Tests for Feedback Service
Translation Quality Analytics & Continuous Improvement Platform

Tests feedback validation rules, taxonomy enforcement, and option selection.
"""

from uuid import uuid4
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base
from src.database.repository import TranslationRepository
from src.feedback.models import FeedbackSubmissionDTO
from src.feedback.service import FeedbackService
from src.translation.models import TranslationOptionDTO, TranslationResultDTO


@pytest.fixture
def test_db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def feedback_service(test_db_session):
    class TestSessionFactory:
        def __init__(self, sess):
            self.sess = sess

        def __enter__(self):
            return self.sess

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                self.sess.commit()
            else:
                self.sess.rollback()

    repo = TranslationRepository(session_factory=lambda: TestSessionFactory(test_db_session))
    return FeedbackService(repository=repo), repo


def test_submit_good_feedback(feedback_service):
    svc, repo = feedback_service
    dto = TranslationResultDTO(
        request_id=uuid4(),
        provider="huggingface",
        source_text="Welcome to our platform.",
        source_language="en",
        target_language="es",
        translation_time_ms=120,
        status="COMPLETED",
        options=[
            TranslationOptionDTO(
                option_id=uuid4(),
                style_option="NATURAL",
                translated_text="Bienvenido a nuestra plataforma.",
                confidence_score=0.95,
            )
        ],
    )
    repo.save_translation(dto)
    opt_id = dto.options[0].option_id

    submission = FeedbackSubmissionDTO(
        option_id=opt_id,
        rating="GOOD",
        comments="Great translation!"
    )
    res = svc.record_feedback(submission)

    assert res.rating == "GOOD"
    assert res.option_id == opt_id
    assert "Thank you" in res.message


def test_submit_poor_feedback_with_reason(feedback_service):
    svc, repo = feedback_service
    dto = TranslationResultDTO(
        request_id=uuid4(),
        provider="huggingface",
        source_text="Welcome to our platform.",
        source_language="en",
        target_language="es",
        translation_time_ms=120,
        status="COMPLETED",
        options=[
            TranslationOptionDTO(
                option_id=uuid4(),
                style_option="LITERAL",
                translated_text="Bienvenida hacia nuestra plataforma.",
                confidence_score=0.75,
            )
        ],
    )
    repo.save_translation(dto)
    opt_id = dto.options[0].option_id

    submission = FeedbackSubmissionDTO(
        option_id=opt_id,
        rating="POOR",
        reason="TOO_LITERAL",
        comments="Unnatural preposition used."
    )
    res = svc.record_feedback(submission)

    assert res.rating == "POOR"
    assert res.reason == "TOO_LITERAL"


def test_submit_poor_feedback_without_reason_fails(feedback_service):
    svc, repo = feedback_service
    dto = TranslationResultDTO(
        request_id=uuid4(),
        provider="huggingface",
        source_text="Test sentence.",
        source_language="en",
        target_language="es",
        translation_time_ms=120,
        status="COMPLETED",
        options=[
            TranslationOptionDTO(
                option_id=uuid4(),
                style_option="NATURAL",
                translated_text="Frase de prueba.",
            )
        ],
    )
    repo.save_translation(dto)
    opt_id = dto.options[0].option_id

    submission = FeedbackSubmissionDTO(
        option_id=opt_id,
        rating="POOR",
        reason=None,
    )
    with pytest.raises(ValueError, match="defect reason must be selected"):
        svc.record_feedback(submission)


def test_select_preferred_option(feedback_service):
    svc, repo = feedback_service
    dto = TranslationResultDTO(
        request_id=uuid4(),
        provider="huggingface",
        source_text="Select option test.",
        source_language="en",
        target_language="de",
        translation_time_ms=110,
        status="COMPLETED",
        options=[
            TranslationOptionDTO(
                option_id=uuid4(),
                style_option="FORMAL",
                translated_text="Optionstest auswählen.",
            )
        ],
    )
    repo.save_translation(dto)
    opt_id = dto.options[0].option_id

    success = svc.select_preferred_option(opt_id)
    assert success is True
