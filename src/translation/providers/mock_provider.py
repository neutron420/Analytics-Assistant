"""
Mock Translation Provider
Translation Quality Analytics & Continuous Improvement Platform

Provides deterministic, offline translation options for unit testing, CI pipelines,
and local development without requiring external API tokens or network connectivity.
"""

import time
from typing import List, Optional, Tuple
from uuid import uuid4

from src.translation.models import TranslationOptionDTO
from src.translation.providers.base import BaseTranslationProvider


# Sample deterministic vocabulary dictionary for realistic mock strings
MOCK_LANGUAGE_DICTIONARIES = {
    "hi": {
        "LITERAL": "[शब्दशः] {text}",
        "NATURAL": "[स्वाभाविक] {text}",
        "FORMAL": "[औपचारिक] {text}",
    },
    "es": {
        "LITERAL": "[Literal] {text}",
        "NATURAL": "[Natural] {text}",
        "FORMAL": "[Formal] {text}",
    },
    "fr": {
        "LITERAL": "[Littérale] {text}",
        "NATURAL": "[Naturelle] {text}",
        "FORMAL": "[Formelle] {text}",
    },
    "de": {
        "LITERAL": "[Wörtlich] {text}",
        "NATURAL": "[Natürlich] {text}",
        "FORMAL": "[Formell] {text}",
    },
    "bn": {
        "LITERAL": "[আক্ষরিক] {text}",
        "NATURAL": "[স্বাভাবিক] {text}",
        "FORMAL": "[আনুষ্ঠানিক] {text}",
    },
    "ja": {
        "LITERAL": "[直訳] {text}",
        "NATURAL": "[自然] {text}",
        "FORMAL": "[丁寧] {text}",
    },
}


class MockTranslationProvider(BaseTranslationProvider):
    """Deterministic, zero-network mock translation provider."""

    @property
    def provider_name(self) -> str:
        return "mock"

    def generate_translations(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
        styles: List[str]
    ) -> Tuple[List[TranslationOptionDTO], Optional[float]]:
        # Simulate slight negligible processing delay (2ms)
        time.sleep(0.002)

        options: List[TranslationOptionDTO] = []
        lang_dict = MOCK_LANGUAGE_DICTIONARIES.get(
            target_lang.lower(),
            {s: f"[{s.title()}] {{text}}" for s in styles}
        )

        for style in styles:
            template = lang_dict.get(style, f"[{style}] {{text}}")
            # Generate styled mock text
            mock_text = template.format(text=source_text.strip())
            
            options.append(
                TranslationOptionDTO(
                    option_id=uuid4(),
                    style_option=style,  # type: ignore
                    translated_text=mock_text,
                    confidence_score=0.95,
                    user_selected=False
                )
            )

        return options, 0.95
