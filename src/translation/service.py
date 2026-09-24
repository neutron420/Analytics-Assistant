"""
Translation Service
Translation Quality Analytics & Continuous Improvement Platform

Core provider-agnostic service orchestrating translation requests, latency measurement,
provider resolution, and normalized result generation.
"""

import logging
import time
from typing import Dict, Optional, Type
from uuid import uuid4

from src.config import config
from src.translation.models import (
    TranslationOptionDTO,
    TranslationRequestDTO,
    TranslationResultDTO,
)
from src.translation.providers.base import BaseTranslationProvider
from src.translation.providers.huggingface_provider import HuggingFaceTranslationProvider
from src.translation.providers.mock_provider import MockTranslationProvider

logger = logging.getLogger("translation_service")


class TranslationService:
    """Provider-agnostic facade orchestrating translation generation and latency tracking."""

    def __init__(
        self,
        provider: Optional[BaseTranslationProvider] = None,
        provider_name: Optional[str] = None
    ):
        """
        Initializes TranslationService.

        Args:
            provider: Explicit BaseTranslationProvider instance. If None, resolves from config.
            provider_name: Override string ('huggingface', 'mock', 'cohere').
        """
        self._provider_registry: Dict[str, Type[BaseTranslationProvider]] = {
            "huggingface": HuggingFaceTranslationProvider,
            "mock": MockTranslationProvider,
        }

        # Lazy register Cohere if optional module exists
        try:
            # pyrefly: ignore [missing-import]
            from src.translation.providers.cohere_provider import CohereTranslationProvider
            self._provider_registry["cohere"] = CohereTranslationProvider
        except ImportError:
            pass

        if provider is not None:
            self._provider = provider
        else:
            selected_name = (provider_name or config.translation_provider).lower()
            self._provider = self._resolve_provider(selected_name)

    def _resolve_provider(self, name: str) -> BaseTranslationProvider:
        """Instantiates provider from registry by name."""
        provider_cls = self._provider_registry.get(name)
        if not provider_cls:
            raise ValueError(
                f"Unknown translation provider '{name}'. "
                f"Available providers: {list(self._provider_registry.keys())}"
            )
        logger.info(f"Initialized TranslationService with provider: {name}")
        return provider_cls()

    @property
    def active_provider(self) -> BaseTranslationProvider:
        """Returns the active provider instance."""
        return self._provider

    def set_provider(self, provider: BaseTranslationProvider) -> None:
        """Dynamically updates the active provider (e.g. for testing)."""
        self._provider = provider
        logger.info(f"Switched active provider to: {provider.provider_name}")

    def translate(self, request: TranslationRequestDTO) -> TranslationResultDTO:
        """
        Executes translation for a request payload, measuring precise round-trip latency.

        Args:
            request: Validated TranslationRequestDTO containing text, languages, and styles.

        Returns:
            Normalized TranslationResultDTO containing candidate options and latency.
        """
        if not request.source_text or not request.source_text.strip():
            raise ValueError("Source text must not be empty.")
        if len(request.source_text) > 5000:
            raise ValueError(f"Source text length ({len(request.source_text)}) exceeds limit of 5,000 characters.")

        req_id = uuid4()
        start_ns = time.perf_counter_ns()

        try:
            options, confidence = self._provider.generate_translations(
                source_text=request.source_text,
                source_lang=request.source_language,
                target_lang=request.target_language,
                styles=request.requested_styles
            )
            status = "COMPLETED"
        except Exception as e:
            logger.error(f"Translation failed via provider {self._provider.provider_name}: {e}")
            raise e
        finally:
            stop_ns = time.perf_counter_ns()
            # Calculate duration in milliseconds, clamped to minimum 1ms
            duration_ms = max(1, int((stop_ns - start_ns) / 1_000_000))

        result = TranslationResultDTO(
            request_id=req_id,
            provider=self._provider.provider_name,  # type: ignore
            source_text=request.source_text,
            source_language=request.source_language,
            target_language=request.target_language,
            translation_time_ms=duration_ms,
            status=status,
            options=options
        )

        logger.info(
            f"[{result.provider}] Translated {len(request.source_text)} chars from "
            f"{request.source_language} to {request.target_language} in {duration_ms}ms "
            f"({len(options)} styles generated)"
        )

        return result
