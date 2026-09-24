"""
Translation Data Transfer Objects (DTOs)
Translation Quality Analytics & Continuous Improvement Platform

Defines typed Pydantic models for request intake, style variants, and provider results.
"""

from datetime import datetime, timezone
from typing import List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


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
    user_selected: bool = Field(default=False, description="Flag indicating if the user selected this variant")


class TranslationResultDTO(BaseModel):
    """Normalized response emitted by TranslationService to UI and database."""
    request_id: UUID = Field(default_factory=uuid4, description="Unique translation request ID")
    provider: Literal["huggingface", "cohere", "mock"] = Field(..., description="Active generation provider")
    source_text: str = Field(..., description="Source text")
    source_language: str = Field(..., description="Source language ISO code")
    target_language: str = Field(..., description="Target language ISO code")
    translation_time_ms: int = Field(..., ge=0, description="Measured roundtrip latency in milliseconds")
    status: Literal["COMPLETED", "FAILED", "TIMEOUT"] = Field(default="COMPLETED", description="Execution status")
    options: List[TranslationOptionDTO] = Field(..., description="Candidate style options")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Request completion timestamp"
    )
