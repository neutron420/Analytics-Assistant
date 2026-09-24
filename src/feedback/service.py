"""
Feedback Service
Translation Quality Analytics & Continuous Improvement Platform

Coordinates feedback intake, validation against taxonomies, and transactional persistence.
"""

import logging
from typing import Optional, Union
from uuid import UUID

from src.database.repository import TranslationRepository, default_repository
from src.feedback.models import FeedbackResponseDTO, FeedbackSubmissionDTO

logger = logging.getLogger(__name__)


class FeedbackService:
    """Business service governing human-in-the-loop qualitative translation evaluation."""

    def __init__(self, repository: Optional[TranslationRepository] = None):
        self.repository = repository or default_repository

    def record_feedback(self, submission: FeedbackSubmissionDTO) -> FeedbackResponseDTO:
        """
        Validates and persists user feedback on a candidate translation option.
        
        Args:
            submission: FeedbackSubmissionDTO containing option_id, rating, reason, and comments.
            
        Returns:
            FeedbackResponseDTO acknowledging submission.
            
        Raises:
            ValueError: If POOR is submitted without a valid defect taxonomy reason.
        """
        if submission.rating == "POOR" and not submission.reason:
            raise ValueError("A defect reason must be selected when rating a translation as 'POOR'.")

        db_feedback = self.repository.record_feedback(
            option_id=submission.option_id,
            rating=submission.rating,
            reason=submission.reason,
            comments=submission.comments,
        )

        logger.info(
            f"Feedback recorded: option={submission.option_id}, rating={submission.rating}, "
            f"reason={submission.reason}"
        )

        return FeedbackResponseDTO(
            feedback_id=db_feedback.id,
            option_id=submission.option_id,
            rating=submission.rating,
            reason=submission.reason,
            created_at=db_feedback.created_at,
            message="Thank you! Your quality feedback has been recorded for continuous platform improvement."
        )

    def select_preferred_option(self, option_id: Union[UUID, str]) -> bool:
        """Marks a candidate style option as the user's preferred choice."""
        updated = self.repository.mark_option_selected(option_id=option_id)
        return updated is not None


# Default singleton instance
default_feedback_service = FeedbackService()
