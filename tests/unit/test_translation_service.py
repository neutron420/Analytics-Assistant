"""
Unit Tests for Translation Service and Provider Abstraction
Translation Quality Analytics & Continuous Improvement Platform

Executes 100% offline using MockTranslationProvider.
"""

import pytest
from uuid import UUID

from src.translation.models import (
    TranslationOptionDTO,
    TranslationRequestDTO,
    TranslationResultDTO,
)
from src.translation.providers.base import BaseTranslationProvider
from src.translation.providers.mock_provider import MockTranslationProvider
from src.translation.service import TranslationService


class TestTranslationModels:
    """Verifies DTO validation logic."""

    def test_valid_request_dto(self):
        req = TranslationRequestDTO(
            source_text="Hello world",
            source_language="en",
            target_language="hi"
        )
        assert req.source_text == "Hello world"
        assert req.source_language == "en"
        assert req.target_language == "hi"
        assert req.requested_styles == ["LITERAL", "NATURAL", "FORMAL"]

    def test_empty_source_text_fails(self):
        with pytest.raises(ValueError):
            TranslationRequestDTO(
                source_text="",
                source_language="en",
                target_language="es"
            )

    def test_oversized_source_text_fails(self):
        with pytest.raises(ValueError):
            TranslationRequestDTO(
                source_text="a" * 5001,
                source_language="en",
                target_language="es"
            )

    def test_translation_option_dto(self):
        opt = TranslationOptionDTO(
            style_option="NATURAL",
            translated_text="Bonjour le monde",
            confidence_score=0.92
        )
        assert isinstance(opt.option_id, UUID)
        assert opt.style_option == "NATURAL"
        assert opt.user_selected is False


class TestMockTranslationProvider:
    """Verifies the deterministic MockTranslationProvider."""

    def test_mock_provider_generation(self):
        provider = MockTranslationProvider()
        assert provider.provider_name == "mock"

        styles = ["LITERAL", "NATURAL", "FORMAL"]
        options, confidence = provider.generate_translations(
            source_text="Machine learning pipelines",
            source_lang="en",
            target_lang="es",
            styles=styles
        )

        assert len(options) == 3
        assert confidence == 0.95
        returned_styles = [opt.style_option for opt in options]
        assert returned_styles == styles
        for opt in options:
            assert "Machine learning pipelines" in opt.translated_text


class TestTranslationServiceFacade:
    """Verifies the provider-agnostic TranslationService orchestrator."""

    def test_service_execution_with_mock(self):
        mock_provider = MockTranslationProvider()
        service = TranslationService(provider=mock_provider)

        req = TranslationRequestDTO(
            source_text="Data engineering at scale",
            source_language="en",
            target_language="fr"
        )
        result = service.translate(req)

        assert isinstance(result, TranslationResultDTO)
        assert result.provider == "mock"
        assert result.status == "COMPLETED"
        assert result.translation_time_ms >= 1
        assert len(result.options) == 3
        assert result.source_text == "Data engineering at scale"

    def test_service_provider_switching(self):
        service = TranslationService(provider_name="mock")
        assert service.active_provider.provider_name == "mock"

        class DummyCustomProvider(BaseTranslationProvider):
            @property
            def provider_name(self) -> str:
                return "custom_dummy"

            def generate_translations(self, text, src, tgt, styles):
                return [], 1.0

        service.set_provider(DummyCustomProvider())
        assert service.active_provider.provider_name == "custom_dummy"
