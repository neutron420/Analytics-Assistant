"""
Base Translation Provider Interface
Translation Quality Analytics & Continuous Improvement Platform

Defines the abstract interface that all translation provider adapters must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from src.translation.models import TranslationOptionDTO


class BaseTranslationProvider(ABC):
    """Abstract base class for all pluggable translation providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the canonical provider name ('huggingface', 'cohere', 'mock')."""
        pass

    @abstractmethod
    def generate_translations(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
        styles: List[str]
    ) -> Tuple[List[TranslationOptionDTO], Optional[float]]:
        """
        Generates candidate translation options for the specified text and styles.

        Args:
            source_text: The input text to be translated.
            source_lang: ISO-639-1 code of the source language (e.g. 'en').
            target_lang: ISO-639-1 code of the target language (e.g. 'hi', 'fr').
            styles: List of stylistic variants requested (e.g. ['LITERAL', 'NATURAL', 'FORMAL']).

        Returns:
            A tuple of:
            - list of TranslationOptionDTO items
            - overall normalized confidence score (float 0.0 - 1.0 or None)
        """
        pass
