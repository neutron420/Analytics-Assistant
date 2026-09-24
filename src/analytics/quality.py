"""
Translation Quality Scoring & Rule-Based Anomaly Detection
Translation Quality Analytics & Continuous Improvement Platform

Provides transparent, project-defined heuristics for scoring translation candidates
and flagging operational anomalies. 

NOTE: This is a project-specific composite scoring heuristic designed for observable
operational tracking, NOT an academic ground-truth MT metric like BLEU or COMET.
"""

from typing import List, Optional, Tuple


QUALITY_CATEGORIES = {
    "EXCELLENT": (88.0, 100.0),
    "GOOD": (75.0, 87.99),
    "NEEDS_REVIEW": (60.0, 74.99),
    "POOR": (0.0, 59.99),
}

# Configurable Anomaly Thresholds
MAX_NORMAL_LATENCY_MS = 12000
MIN_LENGTH_RATIO = 0.35
MAX_LENGTH_RATIO = 3.00
MIN_CONFIDENCE_THRESHOLD = 0.60


def calculate_length_ratio(source_text: str, target_text: str) -> float:
    """Calculates character length ratio between target and source."""
    src_len = len((source_text or "").strip())
    tgt_len = len((target_text or "").strip())
    if src_len == 0:
        return 0.0
    return round(tgt_len / src_len, 3)


def get_quality_category(score: float) -> str:
    """Categorizes a 0-100 score into transparent operational tiers."""
    for category, (low, high) in QUALITY_CATEGORIES.items():
        if low <= score <= high:
            return category
    return "POOR" if score < 60.0 else "EXCELLENT"


def detect_translation_anomalies(
    source_text: str,
    translated_text: str,
    latency_ms: int,
    confidence_score: Optional[float] = None,
    feedback_rating: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """
    Evaluates rule-based operational anomalies on translation execution.

    Anomaly Rules:
    1. EMPTY_OUTPUT: Target text is blank or whitespace.
    2. SLOW_TRANSLATION: Roundtrip latency exceeds normal operational threshold.
    3. UNUSUAL_LENGTH_RATIO: Target/Source length ratio is outside expected expansion/contraction bounds.
    4. LOW_CONFIDENCE: Provider confidence is below acceptable threshold.
    5. QUALITY_DEGRADATION: User recorded a negative (POOR) quality evaluation.
    """
    reasons: List[str] = []

    src_clean = (source_text or "").strip()
    tgt_clean = (translated_text or "").strip()

    # Rule 1: Empty output
    if not tgt_clean and src_clean:
        reasons.append("EMPTY_OUTPUT")

    # Rule 2: Excessive latency
    if latency_ms > MAX_NORMAL_LATENCY_MS:
        reasons.append("SLOW_TRANSLATION")

    # Rule 3: Extreme length expansion or truncation
    if src_clean and tgt_clean:
        ratio = calculate_length_ratio(src_clean, tgt_clean)
        if ratio < MIN_LENGTH_RATIO or ratio > MAX_LENGTH_RATIO:
            reasons.append("UNUSUAL_LENGTH_RATIO")

    # Rule 4: Low model confidence (if provided)
    if confidence_score is not None and confidence_score < MIN_CONFIDENCE_THRESHOLD:
        reasons.append("LOW_CONFIDENCE")

    # Rule 5: User feedback degradation
    if feedback_rating and feedback_rating.upper() == "POOR":
        reasons.append("QUALITY_DEGRADATION")

    return (len(reasons) > 0, reasons)


def compute_composite_quality_score(
    source_text: str,
    translated_text: str,
    latency_ms: int,
    confidence_score: Optional[float] = None,
    feedback_rating: Optional[str] = None,
) -> Tuple[float, str]:
    """
    Computes a project-defined 0-100 composite quality score based on multi-signal indicators:
    
    Formula Breakdown (Base 100 points):
    - Base baseline: 88.0 pts
    - Model Confidence component: up to +8 pts (if confidence is high) or -10 pts (if confidence is low)
    - Length Ratio penalty: -15 pts if ratio is distorted (<0.35 or >3.0)
    - Latency component: -5 pts if latency > 8000ms, -10 pts if latency > 12000ms
    - Human Evaluation component:
        * GOOD feedback: +5 pts (boost for confirmed quality)
        * POOR feedback: -25 pts (strong penalty for user-reported defects)

    Returns:
        Tuple of (score: float, category: str)
    """
    score = 88.0

    src_clean = (source_text or "").strip()
    tgt_clean = (translated_text or "").strip()

    if not tgt_clean:
        return (0.0, "POOR")

    # 1. Confidence component
    if confidence_score is not None:
        if confidence_score >= 0.90:
            score += 4.0
        elif confidence_score < 0.60:
            score -= 10.0

    # 2. Length ratio component
    ratio = calculate_length_ratio(src_clean, tgt_clean)
    if ratio < MIN_LENGTH_RATIO or ratio > MAX_LENGTH_RATIO:
        score -= 15.0

    # 3. Latency component
    if latency_ms > 12000:
        score -= 10.0
    elif latency_ms > 8000:
        score -= 5.0

    # 4. Human feedback component
    if feedback_rating:
        if feedback_rating.upper() == "GOOD":
            score = min(100.0, score + 5.0)
        elif feedback_rating.upper() == "POOR":
            score = max(20.0, score - 28.0)

    # Clamp to [0.0, 100.0]
    final_score = round(max(0.0, min(100.0, score)), 1)
    category = get_quality_category(final_score)

    return (final_score, category)
