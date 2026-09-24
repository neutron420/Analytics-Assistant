"""
Feedback Data Transfer Objects & Domain Models
Translation Quality Analytics & Continuous Improvement Platform

Defines typed schemas for human feedback intake, ratings, and defect taxonomy.
"""

from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


FeedbackRatingType = Literal["GOOD", "POOR"]
DefectReasonType = Literal[
    "INCORRECT_MEANING",
    "GRAMMAR",
    "GRAMMAR_ISSUE",
    "TOO_LITERAL",
    "WRONG_CONTEXT",
    "UNNATURAL_PHRASING",
    "TERMINOLOGY_ISSUE",
    "OTHER",
]


class FeedbackSubmissionDTO(BaseModel):
    """Payload submitted when a user rates a specific translation option."""
    option_id: UUID = Field(..., description="UUID of the translation option being evaluated")
    rating: FeedbackRatingType = Field(..., description="Binary evaluation: GOOD or POOR")
    reason: Optional[DefectReasonType] = Field(
        default=None,
        description="Defect taxonomy code, mandatory when rating is POOR"
    )
    comments: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional qualitative commentary or corrections"
    )


class FeedbackResponseDTO(BaseModel):
    """Response returned upon successfully recording human feedback."""
    feedback_id: UUID = Field(default_factory=uuid4, description="Recorded feedback primary identifier")
    option_id: UUID = Field(..., description="Target option evaluated")
    rating: FeedbackRatingType = Field(..., description="Submitted rating")
    reason: Optional[DefectReasonType] = Field(default=None, description="Submitted defect code")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Persistence timestamp"
    )
    message: str = Field(default="Feedback submitted successfully", description="Status message")
