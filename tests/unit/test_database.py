"""
Unit Tests for Database Connection and Repository
Translation Quality Analytics & Continuous Improvement Platform

Tests repository CRUD operations, transactions, cascade constraints, and feedback validation.
"""

from datetime import datetime, timezone
from uuid import uuid4
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.connection import check_db_health
from src.database.models import Base, Feedback, Translation, TranslationOption
from src.database.repository import TranslationRepository
from src.translation.models import (
    TranslationOptionDTO,
    TranslationRequestDTO,
    TranslationResultDTO,
)


@pytest.fixture
def test_db_session():
    """In-memory SQLite session fixture for isolated fast unit tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def repo(test_db_session):
    """Repository bound to the test session fixture."""
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

    return TranslationRepository(session_factory=lambda: TestSessionFactory(test_db_session))


def create_sample_dto(provider="huggingface") -> TranslationResultDTO:
    req_id = uuid4()
    return TranslationResultDTO(
        request_id=req_id,
        provider=provider,
        source_text="Good morning, have a nice day.",
        source_language="en",
        target_language="fr",
        translation_time_ms=142,
        status="COMPLETED",
        options=[
            TranslationOptionDTO(
                option_id=uuid4(),
                style_option="LITERAL",
                translated_text="Bon matin, ayez une belle journée.",
                confidence_score=0.88,
            ),
            TranslationOptionDTO(
                option_id=uuid4(),
                style_option="NATURAL",
                translated_text="Bonjour, bonne journée.",
                confidence_score=0.96,
            ),
            TranslationOptionDTO(
                option_id=uuid4(),
                style_option="FORMAL",
                translated_text="Bonjour, je vous souhaite une excellente journée.",
                confidence_score=0.92,
            ),
        ],
    )


def test_save_and_get_translation(repo, test_db_session):
    dto = create_sample_dto()
    saved = repo.save_translation(dto, client_ip="192.168.1.10")

    assert saved.id == dto.request_id
    assert saved.provider == "huggingface"
    assert saved.source_text == dto.source_text
    assert saved.translation_time_ms == 142

    # Query back
    fetched = repo.get_translation_by_id(dto.request_id)
    assert fetched is not None
    assert fetched.id == dto.request_id
    assert len(fetched.options) == 3
    styles = {opt.style_option for opt in fetched.options}
    assert styles == {"LITERAL", "NATURAL", "FORMAL"}


def test_record_feedback_good(repo, test_db_session):
    dto = create_sample_dto()
    saved = repo.save_translation(dto)
    option_id = dto.options[1].option_id  # Natural style

    feedback = repo.record_feedback(
        option_id=option_id,
        rating="GOOD",
        comments="Perfect natural translation!"
    )

    assert feedback.option_id == option_id
    assert feedback.rating == "GOOD"
    assert feedback.reason is None
    assert feedback.comments == "Perfect natural translation!"


def test_record_feedback_poor(repo, test_db_session):
    dto = create_sample_dto()
    repo.save_translation(dto)
    option_id = dto.options[0].option_id  # Literal style

    feedback = repo.record_feedback(
        option_id=option_id,
        rating="POOR",
        reason="TOO_LITERAL",
        comments="Literal translation sounds unnatural."
    )

    assert feedback.option_id == option_id
    assert feedback.rating == "POOR"
    assert feedback.reason == "TOO_LITERAL"


def test_record_feedback_invalid_rating(repo, test_db_session):
    dto = create_sample_dto()
    repo.save_translation(dto)
    option_id = dto.options[0].option_id

    with pytest.raises(ValueError, match="Invalid rating"):
        repo.record_feedback(option_id=option_id, rating="EXCELLENT")


def test_record_feedback_invalid_reason(repo, test_db_session):
    dto = create_sample_dto()
    repo.save_translation(dto)
    option_id = dto.options[0].option_id

    with pytest.raises(ValueError, match="Invalid reason"):
        repo.record_feedback(option_id=option_id, rating="POOR", reason="HALLUCINATION")


def test_mark_option_selected(repo, test_db_session):
    dto = create_sample_dto()
    repo.save_translation(dto)
    target_opt_id = dto.options[1].option_id

    updated = repo.mark_option_selected(target_opt_id)
    assert updated is not None
    assert updated.user_selected is True


def test_get_recent_translations(repo, test_db_session):
    dto1 = create_sample_dto()
    dto2 = create_sample_dto()
    repo.save_translation(dto1)
    repo.save_translation(dto2)

    recent = repo.get_recent_translations(limit=5)
    assert len(recent) == 2


def test_db_health_check():
    engine = create_engine("sqlite:///:memory:")
    health = check_db_health(engine)
    assert health["status"] == "healthy"
