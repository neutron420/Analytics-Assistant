"""
Translation Data Transfer Objects (DTOs)
Translation Quality Analytics & Continuous Improvement Platform

Defines typed Pydantic models for request intake, style variants, and provider results.
"""

from datetime import datetime, timezone
from typing import List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def generate_human_request_id(dt: Optional[datetime] = None) -> str:
    """Generates a structured, human-readable trace identifier: REQ-YYYYMMDD-XXXXX."""
    now = dt or datetime.now(timezone.utc)
    short_uuid = uuid4().hex[:5].upper()
    return f"REQ-{now.strftime('%Y%m%d')}-{short_uuid}"


class TranslationRequestDTO(BaseModel):
    """Incoming user translation request payload."""
    source_text: str = Field(..., min_length=1, max_length=5000, description="Source text to translate")
    source_language: str = Field(default="en", max_length=10, description="ISO-639-1 source language code")
    target_language: str = Field(..., min_length=2, max_length=10, description="ISO-639-1 target language code")
    requested_styles: List[Literal["LITERAL", "NATURAL", "FORMAL"]] = Field(
        default=["LITERAL", "NATURAL", "FORMAL"],
        description="Target stylistic variants"
    )


class TranslationOptionDTO(BaseModel):
    """A single candidate translation style variant."""
    option_id: UUID = Field(default_factory=uuid4, description="Unique candidate variant ID")
    style_option: Literal["LITERAL", "NATURAL", "FORMAL"] = Field(..., description="Style classification")
    translated_text: str = Field(..., min_length=1, description="Generated candidate translation")
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Normalized model confidence")
    text_length: int = Field(default=0, description="Character count of translated text")
    user_selected: bool = Field(default=False, description="Flag indicating if the user selected this variant")


class TranslationResultDTO(BaseModel):
    """Normalized response emitted by TranslationService to UI and database."""
    request_id: UUID = Field(default_factory=uuid4, description="Unique internal translation UUID")
    human_request_id: str = Field(default_factory=generate_human_request_id, description="Traceable ID e.g. REQ-20260924-A8F31")
    provider: Literal["huggingface", "cohere", "mock"] = Field(..., description="Active generation provider")
    model: Optional[str] = Field(default=None, description="Model identifier used for generation")
    source_text: str = Field(..., description="Source text")
    source_language: str = Field(..., description="Source language ISO code")
    target_language: str = Field(..., description="Target language ISO code")
    translation_time_ms: int = Field(..., ge=0, description="Measured roundtrip latency in milliseconds")
    quality_score: Optional[float] = Field(default=None, description="Calculated composite quality score 0-100")
    anomaly_flag: bool = Field(default=False, description="Flag indicating if execution hit an anomaly")
    anomaly_reasons: List[str] = Field(default_factory=list, description="List of detected anomaly codes")
    status: Literal["COMPLETED", "FAILED", "TIMEOUT"] = Field(default="COMPLETED", description="Execution status")
    options: List[TranslationOptionDTO] = Field(..., description="Candidate style options")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Request completion timestamp"
    )
