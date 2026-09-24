# Phased Implementation Plan
# Translation Quality Analytics & Continuous Improvement Platform

**Status**: Production-Ready (Phases 1–14 Implemented & Fully Operational)  
**Version**: 2.0.0  
**Phase**: Active Deployment & Observability

> **PLATFORM STATUS:**  
> All core architecture phases (Phases 1–14) are fully implemented, verified, and operational.
> - PostgreSQL database and Grafana containers are active in Docker.
> - Hugging Face translation engine, feedback loop, and redesigned Gradio SaaS UI are live.
> - OPUS-100 baseline data and PySpark ETL batch pipeline are executed and verified.
> - All 25 automated unit tests pass with 100% success rate.
> - Phase 15 (Cohere) remains an optional, non-blocking future extension.

---

## Phase Overview Matrix (Master Implementation)

| Phase | Phase Name | Primary Focus | Status |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **Inspect Current Project** | Codebase inspection & architecture validation | **COMPLETED** |
| **Phase 2** | **Update Documentation** | Living documentation, architecture ADRs & memory | **COMPLETED** |
| **Phase 3** | **Database Schema Improvements** | Model migration (`request_id`, `quality_score`, `anomaly_flag`) | **COMPLETED** |
| **Phase 4** | **Request ID & Traceability** | Unique traceable `REQ-YYYYMMDD-XXXXX` format | **COMPLETED** |
| **Phase 5** | **Translation Persistence** | Database persistence with roundtrip telemetry & lengths | **COMPLETED** |
| **Phase 6** | **Fix Human-Feedback Flow** | Synchronized state, defect taxonomy & POOR requirement | **COMPLETED** |
| **Phase 7** | **Preferred Translation** | User preference persistence & candidate selection tracking | **COMPLETED** |
| **Phase 8** | **Translation Latency Metrics** | Sub-millisecond timing measurement & round-trip logging | **COMPLETED** |
| **Phase 9** | **Quality Scoring** | Transparent composite 0-100 score & 4 operational tiers | **COMPLETED** |
| **Phase 10** | **Anomaly Detection** | Rule-based latency, length distortion & defect triggers | **COMPLETED** |
| **Phase 11** | **Language-Pair Analytics** | Real-time pair throughput, latency & defect aggregates | **COMPLETED** |
| **Phase 12** | **Feedback Analytics** | Granular defect distribution & downvote rates | **COMPLETED** |
| **Phase 13** | **Style Preference Analytics** | Evaluator preference share across Natural/Formal/Literal | **COMPLETED** |
| **Phase 14** | **Quality Investigation Workflow**| Diagnostic deep-dive & audit review by Request ID | **COMPLETED** |
| **Phase 15** | **Session History Improvements** | 8-column historical audit log with Request ID & filters | **COMPLETED** |
| **Phase 16** | **OPUS-100 Dataset Ingestion** | Raw dataset staging under `data/raw/opus100/` | **COMPLETED** |
| **Phase 17** | **PySpark ETL Batch Pipeline** | Big-data cleaning, feature engineering & aggregations | **COMPLETED** |
| **Phase 18** | **ETL Data Quality Report** | Dynamic data quality audit report from real pipeline counts | **COMPLETED** |
| **Phase 19** | **Continuous Improvement Loop** | Automated feedback & style preference insights engine | **COMPLETED** |
| **Phase 20** | **Gradio Analytics Redesign** | Modern dark analytics UI with zero hardcoded fake metrics | **COMPLETED** |
| **Phase 21** | **Grafana Observability Dashboards**| 14 live PostgreSQL monitoring panels auto-refreshing 5s | **COMPLETED** |
| **Phase 22** | **Grafana Alerting** | Configurable alert rules for latency, defects & errors | **COMPLETED** |
| **Phase 23** | **Testing & Validation** | 31/31 unit tests passing (100% pass rate) | **COMPLETED** |
| **Phase 24** | **Docker Verification** | Healthchecked container services (Postgres, Grafana) | **COMPLETED** |
| **Phase 25** | **Final System Verification** | End-to-end integration sequence verified | **COMPLETED** |

---

## Detailed Phase Specifications

### PHASE 1: Documentation and Architecture
- **Goal**: Establish the complete architectural and operational foundation before writing code.
- **Tasks**:
  1. Author all required documentation files in `docs/`.
  2. Create all system and data flow diagrams in `docs/diagrams/`.
  3. Validate internal consistency across schemas, formulas, and pluggable provider choices.
- **Expected Output**: Fully populated `docs/` suite serving as persistent project memory.
- **Validation Criteria**: All architectural questions answered; zero code implementation begun.

---

### PHASE 2: Project Skeleton and Configuration
- **Goal**: Configure a reproducible Python 3.10+ development environment and project skeleton.
- **Tasks**:
  1. Initialize virtual environment in WSL2 / Windows.
  2. Create `requirements.txt` with pinned dependencies (`gradio`, `huggingface-hub`, `pyspark`, `sqlalchemy`, `psycopg2-binary`, `pydantic-settings`, `pytest`).
  3. Set up `.env` from `.env.example` with `TRANSLATION_PROVIDER=huggingface`.
  4. Create skeleton folders (`src/`, `data/`, `grafana/`, `pyspark_jobs/`, `scripts/`, `tests/`).
- **Expected Output**: Running virtualenv, validated library imports.
- **Validation Criteria**: `python -c "import gradio, pyspark, sqlalchemy, huggingface_hub"` succeeds without errors.

---

### PHASE 3: PostgreSQL Database
- **Goal**: Establish the relational persistence layer with provider tracking.
- **Tasks**:
  1. Create `src/database/init_schema.sql` (defining `translations`, `translation_options`, `feedback`, `analytics_*` with `provider` column).
  2. Build SQLAlchemy models in `src/database/models.py`.
  3. Implement connection engine and session factory in `src/database/connection.py`.
- **Expected Output**: Active PostgreSQL tables with primary/foreign keys and indexes.
- **Dependencies**: Phase 2.
- **Validation Criteria**: Automated test inserts and queries a dummy record with provider tag across core tables.

---

### PHASE 4: Translation Abstraction
- **Goal**: Implement the internal provider-agnostic translation service and base interface.
- **Tasks**:
  1. Create `src/translation/providers/base.py` declaring `BaseTranslationProvider`.
  2. Create `src/translation/service.py` implementing `TranslationService`.
  3. Define Pydantic DTOs (`TranslationRequestDTO`, `TranslationResultDTO`, `TranslationOptionDTO`).
  4. Implement latency measurement and provider factory resolver.
- **Expected Output**: Pluggable `TranslationService` capable of delegating to any provider.
- **Dependencies**: Phase 3.
- **Validation Criteria**: Service resolves provider based on configuration without coupling to any external SDK.

---

### PHASE 5: Hugging Face Provider
- **Goal**: Implement the primary translation provider using Hugging Face Inference Providers.
- **Tasks**:
  1. Create `src/translation/providers/huggingface_provider.py` implementing `BaseTranslationProvider`.
  2. Authenticate using `HF_TOKEN` from environment (perm: 'Make calls to Inference Providers').
  3. Build multi-style prompt generating Literal, Natural, and Formal variants.
  4. Implement exponential backoff retry handler for rate limits.
- **Expected Output**: Working `HuggingFaceTranslationProvider` returning normalized results.
- **Dependencies**: Phase 4.
- **Validation Criteria**: Valid API call returns 3 distinct translation styles in under 3.5 seconds.

---

### PHASE 6: Mock Provider
- **Goal**: Implement a deterministic mock provider for testing and offline development.
- **Tasks**:
  1. Create `src/translation/providers/mock_provider.py` implementing `BaseTranslationProvider`.
  2. Return structured Literal, Natural, and Formal candidate strings with simulated latency.
- **Expected Output**: Fast, zero-dependency `MockTranslationProvider`.
- **Dependencies**: Phase 4.
- **Validation Criteria**: Unit tests run and pass without network or token requirements.

---

### PHASE 7: Gradio UI
- **Goal**: Build the user-facing web translation application.
- **Tasks**:
  1. Implement `gradio_app/app.py` using Gradio Blocks.
  2. Wire language selectors, text input, translation display cards, and style radio buttons.
  3. Connect translate button to `TranslationService.translate(...)` (completely provider-agnostic).
- **Expected Output**: Interactive web interface running at `http://localhost:7860`.
- **Dependencies**: Phase 5, Phase 6.
- **Validation Criteria**: User can type text, click translate, and observe 3 styles rendered in the UI.

---

### PHASE 8: Feedback System
- **Goal**: Enable user quality evaluation and defect capture.
- **Tasks**:
  1. Build feedback UI controls in Gradio (Thumbs Up/Down, Reason dropdown, Comments).
  2. Implement `src/feedback/service.py` to persist feedback to PostgreSQL `feedback` table.
  3. Wire dynamic visibility (showing reason dropdown only on POOR rating).
- **Expected Output**: Interactive feedback submission integrated into Gradio.
- **Dependencies**: Phase 7.
- **Validation Criteria**: Submitting feedback persists records to PostgreSQL and displays confirmation.

---

### PHASE 9: OPUS-100 Dataset Ingestion
- **Goal**: Ingest baseline parallel translation records from OPUS-100.
- **Status**: Raw dataset already ingested (68,000 records in `data/raw/opus100/`).
- **Tasks**:
  1. Build `scripts/enrich_baseline.py` to stage Tier-2 simulated operational telemetry.
  2. Output Snappy Parquet partitioned by `target_language` to `data/interim/enriched_baseline/`.
- **Expected Output**: Staged baseline Parquet files ready for PySpark ingestion.
- **Dependencies**: Phase 2.
- **Validation Criteria**: Baseline records load cleanly into Spark with expected schemas.

---

### PHASE 10: PySpark ETL
- **Goal**: Implement distributed big data cleaning, feature engineering, and aggregations.
- **Tasks**:
  1. Build `pyspark_jobs/etl_job.py`.
  2. Ingest baseline Parquet + PostgreSQL operational records.
  3. Compute character lengths, word counts, length ratios, and latency buckets.
  4. Aggregate across date, language pair, style, and provider dimensions.
  5. Egress to PostgreSQL `analytics_daily_metrics`.
- **Expected Output**: Executable PySpark job writing aggregated rows to PostgreSQL.
- **Dependencies**: Phase 9, Phase 3.
- **Validation Criteria**: PySpark job completes in <3 minutes and writes populated metric rows.

---

### PHASE 11: Quality Analytics
- **Goal**: Implement heuristic scoring and anomaly detection.
- **Tasks**:
  1. Code Quality Score formula ($Q$) and category assignments in PySpark pipeline.
  2. Implement anomaly detection logic flagging truncation, hallucinations, and downvotes.
  3. Populate `analytics_anomalies` table.
- **Expected Output**: Quality tiers and flagged anomalies saved to database.
- **Dependencies**: Phase 10.
- **Validation Criteria**: Synthetic anomalies correctly flagged and categorized in database.

---

### PHASE 12: Grafana Dashboard
- **Goal**: Deploy real-time operational and quality analytics dashboards.
- **Tasks**:
  1. Configure PostgreSQL datasource provisioning in `grafana/provisioning/datasources/postgres.yaml`.
  2. Build JSON dashboard definition in `grafana/provisioning/dashboards/translation_quality_dashboard.json`.
  3. Verify all core panels and secondary provider panels query and render data correctly.
- **Expected Output**: Pre-configured Grafana dashboard accessible at `http://localhost:3000`.
- **Dependencies**: Phase 10, Phase 11.
- **Validation Criteria**: Dashboard opens with zero manual configuration; displays time series, latency gauges, and anomaly tables.

---

### PHASE 13: Testing
- **Goal**: Implement full test suite coverage.
- **Tasks**:
  1. Write unit tests for schemas, prompts, heuristics, and MockProvider.
  2. Write integration tests for database and HuggingFace provider.
  3. Write PySpark DataFrame data quality tests.
- **Expected Output**: Automated test suite executed via `pytest`.
- **Dependencies**: Phases 3–12.
- **Validation Criteria**: 100% test pass rate across critical edge cases without live API dependency in unit tests.

---

### PHASE 14: Dockerization
- **Goal**: Ensure clean containerized infrastructure deployment.
- **Tasks**:
  1. Finalize `docker-compose.yml` for PostgreSQL and Grafana.
  2. Validate startup ordering, volume persistence, and network healthchecks.
- **Expected Output**: Single `docker compose up` brings up complete infrastructure.
- **Dependencies**: Phase 13.
- **Validation Criteria**: Services restart cleanly without data loss.

---

### PHASE 15: Optional Cohere Provider
- **Goal**: Implement optional Cohere provider for multi-provider benchmarking.
- **Tasks**:
  1. Implement `src/translation/providers/cohere_provider.py` implementing `BaseTranslationProvider`.
  2. Support `TRANSLATION_PROVIDER=cohere` and `COHERE_API_KEY`.
  3. Write integration tests for Cohere provider.
- **Expected Output**: Pluggable Cohere provider enabled on demand without touching UI, database, or analytics code.
- **Dependencies**: Phase 14 (Non-blocking).
- **Validation Criteria**: Switching `TRANSLATION_PROVIDER=cohere` functions seamlessly.
