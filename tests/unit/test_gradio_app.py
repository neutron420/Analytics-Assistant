"""
Unit Tests for Gradio Application
Translation Quality Analytics & Continuous Improvement Platform

Tests Gradio block instantiation, components, event handlers, and feedback helpers.
"""

from uuid import uuid4
import pytest

from gradio_app.app import (
    create_app,
    load_history_table,
    mark_preferred_variant,
    perform_translation,
    submit_human_feedback,
)
from src.database.models import Base
from src.translation.models import TranslationOptionDTO, TranslationResultDTO


def test_gradio_app_structure():
    """Verifies Gradio block hierarchy and essential components exist."""
    demo = create_app()
    assert demo is not None
    # Blocks has children components
    assert len(demo.children) > 0


def test_perform_translation_empty_input():
    msg, nat, formal, lit, opt_map, radio = perform_translation("", "Hindi (hi)")
    assert "Please enter source text" in msg
    assert opt_map == {}


def test_submit_feedback_without_selection():
    res = submit_human_feedback(
        selected_style=None,
        rating="GOOD",
        reason_code=None,
        comments="Nice",
        option_map={},
    )
    assert "Please select which translation candidate option" in res


def test_submit_poor_feedback_missing_reason():
    opt_id = str(uuid4())
    res = submit_human_feedback(
        selected_style="NATURAL",
        rating="POOR",
        reason_code=None,
        comments="Bad",
        option_map={"NATURAL": opt_id},
    )
    assert "Please choose a specific defect reason" in res


def test_mark_preferred_variant_without_selection():
    res = mark_preferred_variant(None, {})
    assert "Please select a variant option first" in res


def test_load_history_table_returns_list():
    rows = load_history_table()
    assert isinstance(rows, list)
