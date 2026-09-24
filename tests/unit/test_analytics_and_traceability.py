"""
Unit Tests for Quality Scoring, Rule-Based Anomaly Detection & Traceability
Translation Quality Analytics & Continuous Improvement Platform
"""

import pytest
from src.analytics.quality import (
    calculate_length_ratio,
    compute_composite_quality_score,
    detect_translation_anomalies,
    get_quality_category,
)
from src.translation.models import generate_human_request_id
from gradio_app.app import investigate_translation


def test_human_request_id_format():
    """Validates REQ-YYYYMMDD-XXXXX structure."""
    req_id = generate_human_request_id()
    assert req_id.startswith("REQ-")
    parts = req_id.split("-")
    assert len(parts) == 3
    assert len(parts[1]) == 8  # YYYYMMDD
    assert len(parts[2]) == 5  # Short hex


def test_length_ratio_calculation():
    """Validates length ratio computation."""
    assert calculate_length_ratio("Hello world", "Hola mundo") > 0.8
    assert calculate_length_ratio("", "Something") == 0.0
    assert calculate_length_ratio("Source", "") == 0.0


def test_quality_categories():
    """Verifies score categorization thresholds."""
    assert get_quality_category(95.0) == "EXCELLENT"
    assert get_quality_category(82.0) == "GOOD"
    assert get_quality_category(68.0) == "NEEDS_REVIEW"
    assert get_quality_category(45.0) == "POOR"


def test_composite_quality_score():
    """Verifies composite quality scoring logic."""
    # Standard clean translation
    score, cat = compute_composite_quality_score(
        source_text="Hello, how are you?",
        translated_text="नमस्ते, आप कैसे हैं?",
        latency_ms=2500,
        confidence_score=0.92,
        feedback_rating="GOOD",
    )
    assert 85.0 <= score <= 100.0
    assert cat in ["EXCELLENT", "GOOD"]

    # Translation with defect feedback and high latency
    bad_score, bad_cat = compute_composite_quality_score(
        source_text="Hello world",
        translated_text="X",
        latency_ms=15000,
        confidence_score=0.40,
        feedback_rating="POOR",
    )
    assert bad_score < 60.0
    assert bad_cat == "POOR"


def test_anomaly_detection_rules():
    """Verifies rule-based anomaly detection conditions."""
    # Empty output
    is_anom, reasons = detect_translation_anomalies("Hello", "", latency_ms=1000)
    assert is_anom
    assert "EMPTY_OUTPUT" in reasons

    # Excessive latency (> 12000 ms)
    is_anom, reasons = detect_translation_anomalies("Hello", "Hola", latency_ms=14000)
    assert is_anom
    assert "SLOW_TRANSLATION" in reasons

    # Extreme length ratio distortion
    is_anom, reasons = detect_translation_anomalies("Short", "Very long repeated runaway translation " * 10, latency_ms=1000)
    assert is_anom
    assert "UNUSUAL_LENGTH_RATIO" in reasons

    # Low confidence
    is_anom, reasons = detect_translation_anomalies("Hello", "Hola", latency_ms=1000, confidence_score=0.45)
    assert is_anom
    assert "LOW_CONFIDENCE" in reasons

    # User feedback degradation
    is_anom, reasons = detect_translation_anomalies("Hello", "Hola", latency_ms=1000, feedback_rating="POOR")
    assert is_anom
    assert "QUALITY_DEGRADATION" in reasons


def test_investigate_empty_id():
    """Verifies investigation empty state."""
    summary, req_id, *_ = investigate_translation("")
    assert "Please enter a Request ID" in summary
    assert req_id == "—"
