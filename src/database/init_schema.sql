-- ==============================================================================
-- POSTGRESQL INITIAL SCHEMA
-- Translation Quality Analytics & Continuous Improvement Platform
-- ==============================================================================

-- Enable UUID extension if not already available
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Table: translations
CREATE TABLE IF NOT EXISTS translations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(30) NOT NULL DEFAULT 'huggingface',
    source_text TEXT NOT NULL,
    source_language VARCHAR(10) NOT NULL,
    target_language VARCHAR(10) NOT NULL,
    translation_time_ms INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'COMPLETED',
    client_ip VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_translations_created_at ON translations (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_translations_pair ON translations (source_language, target_language);
CREATE INDEX IF NOT EXISTS idx_translations_provider ON translations (provider);

-- 2. Table: translation_options
CREATE TABLE IF NOT EXISTS translation_options (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    translation_id UUID NOT NULL REFERENCES translations(id) ON DELETE CASCADE,
    style_option VARCHAR(30) NOT NULL,
    translated_text TEXT NOT NULL,
    confidence_score REAL,
    user_selected BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_options_translation_id ON translation_options (translation_id);
CREATE INDEX IF NOT EXISTS idx_options_style ON translation_options (style_option);

-- 3. Table: feedback
CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    option_id UUID NOT NULL REFERENCES translation_options(id) ON DELETE CASCADE,
    rating VARCHAR(10) NOT NULL CHECK (rating IN ('GOOD', 'POOR')),
    reason VARCHAR(30) CHECK (reason IN ('INCORRECT_MEANING', 'GRAMMAR', 'TOO_LITERAL', 'WRONG_CONTEXT', 'OTHER') OR reason IS NULL),
    comments TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feedback_option_id ON feedback (option_id);
CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback (created_at DESC);

-- 4. Table: analytics_daily_metrics (Aggregated mart populated by PySpark)
CREATE TABLE IF NOT EXISTS analytics_daily_metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_date DATE NOT NULL,
    provider VARCHAR(30) NOT NULL,
    source_language VARCHAR(10) NOT NULL,
    target_language VARCHAR(10) NOT NULL,
    style_option VARCHAR(30) NOT NULL,
    total_requests BIGINT NOT NULL,
    avg_latency_ms REAL NOT NULL,
    p95_latency_ms REAL NOT NULL,
    avg_quality_score REAL NOT NULL,
    good_feedback_count BIGINT NOT NULL,
    poor_feedback_count BIGINT NOT NULL,
    poor_feedback_rate REAL NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_daily_metrics_slice UNIQUE (metric_date, provider, source_language, target_language, style_option)
);

CREATE INDEX IF NOT EXISTS idx_daily_metrics_lookup ON analytics_daily_metrics (metric_date, source_language, target_language);
CREATE INDEX IF NOT EXISTS idx_daily_metrics_provider ON analytics_daily_metrics (provider);

-- 5. Table: analytics_anomalies (Outliers & flagged low-quality rows)
CREATE TABLE IF NOT EXISTS analytics_anomalies (
    id BIGSERIAL PRIMARY KEY,
    translation_id UUID REFERENCES translations(id) ON DELETE SET NULL,
    option_id UUID REFERENCES translation_options(id) ON DELETE SET NULL,
    anomaly_type VARCHAR(50) NOT NULL,
    anomaly_score REAL NOT NULL,
    diagnostic_details TEXT,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_anomalies_detected_at ON analytics_anomalies (detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomalies_type ON analytics_anomalies (anomaly_type);
