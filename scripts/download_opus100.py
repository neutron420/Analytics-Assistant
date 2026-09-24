#!/usr/bin/env python3
"""
OPUS-100 Dataset Ingestion Script
Translation Quality Analytics & Improvement Platform

Downloads target language-pair subsets of the OPUS-100 parallel translation corpus
from Helsinki-NLP/opus-100, cleans basic whitespace/nulls, and writes normalized
Tier-1 Base Corpus JSONL files to data/raw/opus100/<pair>/train.jsonl.

Strict Tier-1 Schema:
{
  "source_text": str,
  "translated_text": str,
  "source_language": str,
  "target_language": str
}
"""

import argparse
import json
import logging
import os
import sys
import unicodedata
from pathlib import Path
from typing import Dict, Any, List

from datasets import load_dataset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("opus100_downloader")

# Config mapping ensuring correct HuggingFace builder config lookup
# Hugging Face names configs in alphabetical order (e.g. bn-en, de-en, en-es)
LANGUAGE_PAIR_CONFIGS: Dict[str, Dict[str, Any]] = {
    "en-hi": {"hf_config": "en-hi", "src": "en", "tgt": "hi", "target_count": 12000},
    "en-es": {"hf_config": "en-es", "src": "en", "tgt": "es", "target_count": 12000},
    "en-fr": {"hf_config": "en-fr", "src": "en", "tgt": "fr", "target_count": 12000},
    "en-de": {"hf_config": "de-en", "src": "en", "tgt": "de", "target_count": 12000},
    "en-bn": {"hf_config": "bn-en", "src": "en", "tgt": "bn", "target_count": 10000},
    "en-ja": {"hf_config": "en-ja", "src": "en", "tgt": "ja", "target_count": 10000},
}


def sanitize_text(text: Any) -> str:
    """Normalizes Unicode to NFC and strips trailing/leading whitespace."""
    if not isinstance(text, str):
        return ""
    normalized = unicodedata.normalize("NFC", text)
    return normalized.strip()


def validate_pair(source_text: str, target_text: str) -> bool:
    """Validates baseline text constraints per docs/DATASET.md."""
    if not source_text or not target_text:
        return False
    if len(source_text) < 1 or len(source_text) > 5000:
        return False
    if len(target_text) < 1 or len(target_text) > 5000:
        return False
    return True


def ingest_language_pair(
    pair_code: str,
    target_count: int,
    output_base_dir: Path
) -> Dict[str, Any]:
    """Streams and persists clean pairs for a single language pair."""
    cfg = LANGUAGE_PAIR_CONFIGS.get(pair_code)
    if not cfg:
        logger.error(f"Unknown language pair {pair_code}. Available: {list(LANGUAGE_PAIR_CONFIGS.keys())}")
        return {"pair": pair_code, "status": "FAILED", "error": "Unknown pair", "count": 0}

    hf_config = cfg["hf_config"]
    src_lang = cfg["src"]
    tgt_lang = cfg["tgt"]

    pair_dir = output_base_dir / pair_code
    pair_dir.mkdir(parents=True, exist_ok=True)
    out_file = pair_dir / "train.jsonl"

    logger.info(f"Starting ingestion for {pair_code} (HF config: {hf_config}, Target: {target_count:,} records)...")
    
    collected = 0
    skipped = 0
    total_src_chars = 0
    total_tgt_chars = 0
    seen_hashes = set()

    try:
        # Load dataset in streaming mode
        ds = load_dataset("Helsinki-NLP/opus-100", hf_config, split="train", streaming=True)
    except Exception as e:
        logger.error(f"Failed to initialize streaming dataset for {pair_code} ({hf_config}): {e}")
        return {
            "pair": pair_code,
            "status": "FAILED",
            "error": str(e),
            "count": 0
        }

    with open(out_file, "w", encoding="utf-8") as f:
        for item in ds:
            trans = item.get("translation", {})
            raw_src = trans.get(src_lang)
            raw_tgt = trans.get(tgt_lang)

            clean_src = sanitize_text(raw_src)
            clean_tgt = sanitize_text(raw_tgt)

            if not validate_pair(clean_src, clean_tgt):
                skipped += 1
                continue

            # Deduplication on (clean_src)
            src_hash = hash(clean_src)
            if src_hash in seen_hashes:
                skipped += 1
                continue
            seen_hashes.add(src_hash)

            record = {
                "source_text": clean_src,
                "translated_text": clean_tgt,
                "source_language": src_lang,
                "target_language": tgt_lang
            }

            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            collected += 1
            total_src_chars += len(clean_src)
            total_tgt_chars += len(clean_tgt)

            if collected % 2000 == 0 or collected == target_count:
                logger.info(f"[{pair_code}] Ingested {collected:,} / {target_count:,} pairs (Skipped: {skipped:,})")

            if collected >= target_count:
                break

    file_size_bytes = out_file.stat().st_size
    file_size_mb = file_size_bytes / (1024 * 1024)

    logger.info(
        f"Completed {pair_code}: {collected:,} records saved to {out_file} "
        f"({file_size_mb:.2f} MB, skipped {skipped:,} invalid/duplicate rows)"
    )

    return {
        "pair": pair_code,
        "status": "COMPLETED",
        "records_count": collected,
        "skipped_count": skipped,
        "file_size_mb": round(file_size_mb, 2),
        "file_path": str(out_file),
        "avg_source_char_len": round(total_src_chars / max(collected, 1), 1),
        "avg_target_char_len": round(total_tgt_chars / max(collected, 1), 1),
    }


def main():
    parser = argparse.ArgumentParser(description="Ingest OPUS-100 subsets for Translation Analytics")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/raw/opus100",
        help="Target base directory for raw JSONL files"
    )
    parser.add_argument(
        "--pairs",
        type=str,
        default=",".join(LANGUAGE_PAIR_CONFIGS.keys()),
        help="Comma-separated language pairs (e.g. en-hi,en-es,en-fr,en-de,en-bn,en-ja)"
    )
    parser.add_argument(
        "--limit-override",
        type=int,
        default=None,
        help="Override record limit for each pair (useful for testing or specific volume targets)"
    )

    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    pair_list = [p.strip() for p in args.pairs.split(",") if p.strip()]

    logger.info("==================================================================")
    logger.info("PHASE 2: OPUS-100 DATASET INGESTION")
    logger.info(f"Target pairs: {pair_list}")
    logger.info(f"Output directory: {output_dir.resolve()}")
    logger.info("==================================================================")

    results: List[Dict[str, Any]] = []
    total_records = 0
    total_size_mb = 0.0

    for pair in pair_list:
        cfg = LANGUAGE_PAIR_CONFIGS.get(pair, {})
        target_limit = args.limit_override or cfg.get("target_count", 10000)
        res = ingest_language_pair(pair, target_limit, output_dir)
        results.append(res)
        total_records += res.get("records_count", 0)
        total_size_mb += res.get("file_size_mb", 0.0)

    # Write manifest summary
    manifest_path = output_dir / "manifest.json"
    manifest_data = {
        "dataset_name": "OPUS-100",
        "source_repo": "Helsinki-NLP/opus-100",
        "total_records": total_records,
        "total_size_mb": round(total_size_mb, 2),
        "pairs_summary": results
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

    logger.info("==================================================================")
    logger.info("INGESTION COMPLETE SUMMARY:")
    logger.info(f"Total pairs ingested: {total_records:,}")
    logger.info(f"Total disk usage: {total_size_mb:.2f} MB")
    logger.info(f"Manifest written to: {manifest_path}")
    logger.info("==================================================================")


if __name__ == "__main__":
    main()
