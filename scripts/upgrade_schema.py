"""
Database Schema Upgrade Script
Translation Quality Analytics & Continuous Improvement Platform

Adds request_id, model, quality_score, anomaly_flag, and metadata columns.
"""

import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import text
from src.database.connection import get_db_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("schema_upgrade")


def upgrade_schema():
    logger.info("Upgrading PostgreSQL schema...")
    with get_db_session() as sess:
        # 1. translations table extensions
        sess.execute(text("ALTER TABLE translations ADD COLUMN IF NOT EXISTS request_id VARCHAR(50);"))
        sess.execute(text("ALTER TABLE translations ADD COLUMN IF NOT EXISTS model VARCHAR(100);"))
        sess.execute(text("ALTER TABLE translations ADD COLUMN IF NOT EXISTS quality_score REAL;"))
        sess.execute(text("ALTER TABLE translations ADD COLUMN IF NOT EXISTS anomaly_flag BOOLEAN DEFAULT FALSE;"))
        sess.execute(text("ALTER TABLE translations ADD COLUMN IF NOT EXISTS anomaly_reasons TEXT;"))

        # Backfill request_id for any existing rows
        sess.execute(text("""
            UPDATE translations 
            SET request_id = 'REQ-' || to_char(created_at, 'YYYYMMDD') || '-' || upper(substring(id::text, 1, 5))
            WHERE request_id IS NULL;
        """))
        sess.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_translations_request_id ON translations(request_id);"))
        sess.execute(text("CREATE INDEX IF NOT EXISTS idx_translations_model ON translations(model);"))

        # 2. translation_options table extensions
        sess.execute(text("ALTER TABLE translation_options ADD COLUMN IF NOT EXISTS text_length INTEGER;"))
        sess.execute(text("UPDATE translation_options SET text_length = length(translated_text) WHERE text_length IS NULL;"))

        # 3. feedback table - drop restrictive enum/check constraints if any to allow extended defect taxonomies
        sess.execute(text("ALTER TABLE feedback DROP CONSTRAINT IF EXISTS feedback_reason_check;"))
        sess.execute(text("ALTER TABLE feedback ALTER COLUMN reason TYPE VARCHAR(50);"))

        logger.info("PostgreSQL schema successfully upgraded and indexed.")


if __name__ == "__main__":
    upgrade_schema()
