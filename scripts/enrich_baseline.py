"""
Baseline Dataset Enrichment Pipeline
Translation Quality Analytics & Continuous Improvement Platform

Transforms raw OPUS-100 JSONL pairs into feature-engineered, cleansed Parquet files
stored in data/interim/enriched_baseline/.
"""

import json
import logging
import os
import sys
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

# Ensure PySpark uses standard python binary
os.environ.setdefault("PYSPARK_PYTHON", "python")
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", "python")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("enrich_baseline")

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw" / "opus100"
OUT_DIR = BASE_DIR / "data" / "interim" / "enriched_baseline"

LANGUAGE_PAIRS = ["en-hi", "en-es", "en-fr", "en-de", "en-bn", "en-ja"]


def compute_length_consistency_score(ratio: float, target_lang: str) -> float:
    """
    Computes linguistic length consistency penalty score (0 to 100).
    Expected ratios relative to English:
    - Romance/Germanic (es, fr, de): 1.0 - 1.3
    - Indic (hi, bn): 0.8 - 1.4
    - CJK / Japanese (ja): 0.4 - 0.9 (character density)
    """
    if target_lang == "ja":
        expected_min, expected_max = 0.35, 1.1
    elif target_lang in ("hi", "bn"):
        expected_min, expected_max = 0.65, 1.6
    else:
        expected_min, expected_max = 0.8, 1.5

    if expected_min <= ratio <= expected_max:
        return 100.0
    elif ratio < expected_min:
        # Severe truncation
        diff = expected_min - ratio
        return max(10.0, 100.0 - diff * 150.0)
    else:
        # Repetition / Hallucination
        diff = ratio - expected_max
        return max(10.0, 100.0 - diff * 80.0)


def compute_quality_score(confidence: float, length_score: float, feedback_score: float) -> float:
    """
    Deterministic quality score Q = 0.35*C + 0.35*S_l + 0.30*S_f
    """
    return round((0.35 * confidence) + (0.35 * length_score) + (0.30 * feedback_score), 2)


def enrich_dataset():
    """Reads raw JSONL files, performs feature engineering, and writes clean Parquet."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Starting baseline enrichment from {RAW_DIR} to {OUT_DIR}")

    total_records = 0
    anomalies_count = 0

    for pair in LANGUAGE_PAIRS:
        src_lang, tgt_lang = pair.split("-")
        pair_file = RAW_DIR / pair / "train.jsonl"
        if not pair_file.exists():
            logger.warning(f"File {pair_file} not found, skipping.")
            continue

        records = []
        seen_hashes = set()

        with open(pair_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue

                src_text = obj.get("source_text", "").strip()
                tgt_text = (obj.get("translated_text") or obj.get("target_text") or "").strip()

                if not src_text or not tgt_text:
                    continue

                # Deduplication
                norm_key = (src_lang, tgt_lang, src_text.lower())
                if norm_key in seen_hashes:
                    continue
                seen_hashes.add(norm_key)

                # Feature engineering
                src_char_len = len(src_text)
                tgt_char_len = len(tgt_text)
                src_word_count = len(src_text.split())
                tgt_word_count = len(tgt_text.split())
                length_ratio = round(tgt_char_len / max(1, src_char_len), 4)

                confidence_score = 90.0  # Normalized baseline confidence
                length_score = compute_length_consistency_score(length_ratio, tgt_lang)
                feedback_factor = 85.0  # Neutral baseline
                quality_score = compute_quality_score(confidence_score, length_score, feedback_factor)

                # Anomaly classification
                is_anomaly = False
                anomaly_type = None
                if length_ratio < 0.25:
                    is_anomaly = True
                    anomaly_type = "LENGTH_TRUNCATION"
                elif length_ratio > 3.5:
                    is_anomaly = True
                    anomaly_type = "RUNAWAY_EXPANSION"
                elif quality_score < 50.0:
                    is_anomaly = True
                    anomaly_type = "LOW_QUALITY_SCORE"

                if is_anomaly:
                    anomalies_count += 1

                records.append({
                    "provider": "opus100_baseline",
                    "source_language": src_lang,
                    "target_language": tgt_lang,
                    "source_text": src_text,
                    "translated_text": tgt_text,
                    "style_option": "NATURAL",
                    "source_char_len": src_char_len,
                    "target_char_len": tgt_char_len,
                    "source_word_count": src_word_count,
                    "target_word_count": tgt_word_count,
                    "length_ratio": length_ratio,
                    "translation_time_ms": 150,  # Nominal benchmark baseline
                    "confidence_score": 0.90,
                    "quality_score": quality_score,
                    "is_anomaly": is_anomaly,
                    "anomaly_type": anomaly_type or "NONE",
                    "created_at": "2026-09-24T00:00:00Z"
                })

        pair_out_dir = OUT_DIR / f"target_language={tgt_lang}"
        pair_out_dir.mkdir(parents=True, exist_ok=True)
        out_parquet = pair_out_dir / "part-00000.parquet"

        # Write high-performance Arrow Parquet
        table = pa.Table.from_pylist(records)
        pq.write_table(table, out_parquet, compression="snappy")
        total_records += len(records)
        logger.info(f"[{pair}] Enriched {len(records):,} records -> {out_parquet.name}")

    summary = {
        "total_enriched_records": total_records,
        "anomalies_flagged": anomalies_count,
        "output_directory": str(OUT_DIR),
        "status": "COMPLETED",
    }
    manifest_path = OUT_DIR / "_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Enrichment completed: {total_records:,} records processed, {anomalies_count:,} anomalies flagged.")
    return summary


if __name__ == "__main__":
    enrich_dataset()
