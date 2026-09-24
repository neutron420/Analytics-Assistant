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

from src.analytics.quality import compute_composite_quality_score, detect_translation_anomalies
from src.config import config
from src.translation.models import (
    TranslationOptionDTO,
    TranslationRequestDTO,
    TranslationResultDTO,
    generate_human_request_id,
)
from src.translation.providers.base import BaseTranslationProvider
from src.translation.providers.huggingface_provider import HuggingFaceTranslationProvider
from src.translation.providers.mock_provider import MockTranslationProvider

logger = logging.getLogger("translation_service")

LANGUAGE_NAMES: Dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "bn": "Bengali",
    "ja": "Japanese",
}


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

        src_lower = request.source_language.lower().strip()
        tgt_lower = request.target_language.lower().strip()

        if src_lower not in LANGUAGE_NAMES:
            raise ValueError(f"Unsupported source language '{request.source_language}'. Supported: {list(LANGUAGE_NAMES.keys())}")
        if tgt_lower not in LANGUAGE_NAMES:
            raise ValueError(f"Unsupported target language '{request.target_language}'. Supported: {list(LANGUAGE_NAMES.keys())}")

        req_uuid = uuid4()
        human_req_id = generate_human_request_id()
        start_ns = time.perf_counter_ns()

        try:
            options, confidence = self._provider.generate_translations(
                source_text=request.source_text,
                source_lang=src_lower,
                target_lang=tgt_lower,
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

        # Compute character lengths on options
        for opt in options:
            opt.text_length = len((opt.translated_text or "").strip())

        # Quality scoring and anomaly detection on primary candidate
        primary_candidate = next((o.translated_text for o in options if o.style_option == "NATURAL"), options[0].translated_text if options else "")
        is_anomaly, anomaly_reasons = detect_translation_anomalies(
            source_text=request.source_text,
            translated_text=primary_candidate,
            latency_ms=duration_ms,
            confidence_score=confidence,
        )
        q_score, _ = compute_composite_quality_score(
            source_text=request.source_text,
            translated_text=primary_candidate,
            latency_ms=duration_ms,
            confidence_score=confidence,
        )

        model_name = getattr(self._provider, "model", config.hf_model if self._provider.provider_name == "huggingface" else None)

        result = TranslationResultDTO(
            request_id=req_uuid,
            human_request_id=human_req_id,
            provider=self._provider.provider_name,  # type: ignore
            model=model_name,
            source_text=request.source_text,
            source_language=src_lower,
            target_language=tgt_lower,
            translation_time_ms=duration_ms,
            quality_score=q_score,
            anomaly_flag=is_anomaly,
            anomaly_reasons=anomaly_reasons,
            status=status,
            options=options,
        )

        logger.info(
            f"[{result.provider}|{result.human_request_id}] Translated {len(request.source_text)} chars from "
            f"{src_lower} to {tgt_lower} in {duration_ms}ms (Quality: {q_score}, Anomalies: {anomaly_reasons})"
        )

        return result


# Singleton instance using environment configuration
default_translation_service = TranslationService()
