# ==============================================================================
# PROJECT MEMORY & LIVING SOURCE OF TRUTH
# Translation Quality Analytics & Continuous Improvement Platform
# ==============================================================================

> **CRITICAL DIRECTIVE FOR ALL AI AGENTS & DEVELOPERS:**
> Before modifying the project, every AI agent MUST read `PROJECT_MEMORY.md` and the relevant documentation files in `docs/`.
> Never implement features, alter database schemas, add dependencies, or write code without aligning with the architecture decisions and rules documented here.

---

## 1. Project Objective
The **Translation Quality Analytics & Continuous Improvement Platform** is an end-to-end engineering system designed to bridge real-time AI translation services with batch big-data analytics and human-in-the-loop feedback.

The platform executes a unified workflow:
1. A user enters text and language preferences via a clean **Gradio UI**.
2. A provider-agnostic **TranslationService** dispatches translation requests to a pluggable provider backend (**Hugging Face Inference Providers** by default, with **MockProvider** for local testing and **Cohere** as an optional future provider).
3. The service generates multiple translation variants (Literal, Natural / Idiomatic, Formal / Context-aware).
4. The user selects their preferred translation and optionally provides qualitative feedback (e.g., Good/Poor with specific failure taxonomy).
5. Real-time translation requests, options, user selections, provider tag, and telemetry are persisted into **PostgreSQL**.
6. Concurrently, a foundational translation corpus (**OPUS-100** subset) is staged and enriched with simulated production metadata to provide baseline benchmark volume.
7. A **PySpark ETL & Analytics Pipeline** periodically ingests historical data and application logs to compute translation quality indicators, latency profiles, length ratios, anomaly flags, and aggregated language-pair metrics.
8. Processed metrics are surfaced through **Grafana Dashboards** for observability, operational monitoring, and quality tracking.
9. The aggregated insights systematically inform prompt engineering and translation service tuning (feedback loop).

---

## 2. Problem Statement
Production machine translation systems face severe observability gaps:
- **Black-box generation**: Generic LLM or MT API calls lack systematic latency, length distortion, and confidence monitoring across diverse language pairs.
- **Provider Lock-in**: Hardcoding client logic to a single paid proprietary API (such as Cohere) prevents switching to accessible or unified infrastructure when billing/payment hurdles arise.
- **Disconnected User Feedback**: When users encounter awkward, grammatically flawed, or culturally inappropriate translations, feedback rarely links back to structured data pipelines.
- **Lack of Scale Analytics**: Small-scale apps store translations in flat logs or simple relational tables without leveraging scalable data processing (e.g., Apache Spark) to detect systematic language-pair quality degradation.
- **Unvalidated Quality Metrics**: Organizations either lack translation quality tracking or overcomplicate it with opaque neural metrics that cannot be easily audited or tied to operational SLAs.

---

## 3. Project Scope
- **Interactive UI**: Gradio web interface for text translation, style variant selection, and explicit feedback submission.
- **Pluggable Translation Architecture**: Clean provider abstraction supporting:
  - **Hugging Face Inference Providers** (Default / Primary provider for development).
  - **MockTranslationProvider** (Testing, local offline development, CI).
  - **CohereTranslationProvider** (Optional / Future provider).
- **Relational Persistence**: PostgreSQL for storing requests, candidate options, provider metadata, selections, and granular feedback.
- **Baseline Corpus**: Staged OPUS-100 dataset subset (68,000 pairs across prioritized English-centric pairs) enriched with telemetry metadata.
- **Big Data Processing**: PySpark batch pipeline executing cleaning, normalization, feature derivation, quality heuristics, and dimensional aggregations.
- **Observability**: Grafana dashboards connected to PostgreSQL (aggregated analytics tables) displaying volume, latency, feedback rates, quality distributions, anomalies, and provider breakdowns.
- **Operational Loop**: Documented feedback taxonomy that drives systematic prompt refinement.

---

## 4. Non-Goals (What This Project Is NOT)
- **NO Custom Model Training/Fine-Tuning**: We are not training translation neural networks from scratch or running LLM fine-tuning loops.
- **NO Direct Provider Coupling**: The Gradio UI, feedback system, database, and PySpark ETL must NEVER import or depend directly on Hugging Face or Cohere SDKs.
- **NO Mandatory Paid Billing**: The project does not require paid production billing setups or proprietary accounts to develop and test.
- **NO React/Next.js/Vite Frontend**: The user interface is strictly Gradio. No separate JavaScript/TypeScript single-page applications will be built.
- **NO Distributed Kubernetes Cluster**: Local execution is powered by Windows WSL2 / Docker Compose; multi-node Kubernetes clusters are out of scope.
- **NO Colab Dependency**: All scripts and pipelines must run reproducibly in the local environment, not in ephemeral cloud notebooks.
- **NO Unnecessary Microservices**: The backend is a modular Python monolith with clearly decoupled layers (Service, Repository, ETL).

---

## 5. Technology Stack Summary
| Layer | Technology | Justification |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ (Current: 3.12) | Unified language for ML APIs, Gradio, and PySpark |
| **User Interface** | Gradio | Rapid, elegant, Python-native UI with zero frontend JS build overhead |
| **Translation Engine** | Hugging Face Inference Providers (Default) | Unified inference API with accessible development allowance |
| **Optional LLM** | Cohere API (Optional / Future) | Available as pluggable alternative; requires zero UI/analytics code changes |
| **Test Engine** | Mock Translation Provider | Deterministic, offline local development and automated testing |
| **Relational Database** | PostgreSQL 15+ | Robust ACID storage, relational constraints for options/feedback, Grafana support |
| **Big Data Engine** | Apache Spark (PySpark 3.4+) | Distributed batch data cleaning, feature engineering, and aggregations |
| **Metrics & Dashboards**| Grafana | Industry-standard operational dashboards directly queryable via PostgreSQL |
| **Containerization** | Docker & Docker Compose | Seamless orchestrator for PostgreSQL and Grafana services |
| **Host Environment** | Windows 11 + WSL2 (Ubuntu) | Production-grade Linux compatibility on a Windows host |

---

## 6. Architecture & Translation Provider Decisions
- **Translation Provider Strategy**:
  - **Hugging Face Inference Providers** is the **default provider** for development.
  - **Cohere** remains an **optional future provider**.
  - **MockTranslationProvider** is used for unit tests, offline development, and CI.
  - All providers implement the internal `BaseTranslationProvider` interface and are orchestrated by `TranslationService`.
  - Provider selection is controlled strictly via environment variable `TRANSLATION_PROVIDER=huggingface` (or `cohere`, `mock`).
  - No provider-specific logic leaks into Gradio UI, feedback handling, database tables, or PySpark jobs.
  - The system switches providers without touching UI or analytics code.
- **ADR-001: Gradio over React/Next.js** — Keeps the entire system maintainable within Python, eliminating JS build toolchains.
- **ADR-002 & 003: OPUS-100 Subset** — Leverages a gold-standard academic corpus (68,000 pairs ingested) without multi-gigabyte disk waste.
- **ADR-004: PySpark for Batch Analytics** — Demonstrates distributed computing design patterns for translation feature engineering.
- **ADR-005: PostgreSQL Relational Persistence** — Guarantees relational integrity between translations, multi-variant options, and feedback.
- **ADR-006: Grafana for Metrics** — Decouples analytics visualization from user interaction.
- **ADR-009 & 010: No Scratch Model / Prompt-Driven Iteration** — Realistically utilizes foundation LLMs with analytical prompt iteration rather than claiming unfeasible fine-tuning.
- **ADR-011: Provider-Agnostic Abstraction with Hugging Face Default** — Eliminates blocking on proprietary billing flows while preserving future provider extensibility.

---

## 7. Dataset Strategy (Base vs. Metadata vs. Derived)
The system maintains strict boundaries across data origins:
1. **Base Dataset (OPUS-100)**: Provides ONLY `source_text`, `translated_text`, `source_language`, `target_language`. (Never invent non-existent OPUS-100 fields).
2. **Application Metadata**: Generated at runtime by translation service and Gradio: `request_id`, `provider`, `translation_time_ms`, `confidence_score`, `style_option`, `user_selected`, `feedback_rating`, `feedback_reason`, `created_at`.
3. **PySpark Derived Features**: Computed strictly in Spark: character lengths, word counts, `length_ratio`, `quality_score`, `quality_category`, `performance_category`, `anomaly_flag`.

Prioritized English-centric pairs (ingested in Phase 2):
- English $\to$ Hindi (`en-hi`) — 12,000 pairs
- English $\to$ Spanish (`en-es`) — 12,000 pairs
- English $\to$ French (`en-fr`) — 12,000 pairs
- English $\to$ German (`en-de`) — 12,000 pairs
- English $\to$ Bengali (`en-bn`) — 10,000 pairs
- English $\to$ Japanese (`en-ja`) — 10,000 pairs
- **Total Ingested**: 68,000 pairs (16.99 MB in `data/raw/opus100/`)

---

## 8. Database Strategy
Normalized schema hosted in PostgreSQL:
- `translations`: Core translation requests, input parameters, provider (`huggingface`, `cohere`, `mock`), latency, and status.
- `translation_options`: Multiple generated options (Literal, Natural, Formal) linked via `translation_id`.
- `feedback`: User ratings (GOOD / POOR), failure taxonomy, optional comments.
- `analytics_daily_metrics`: PySpark-aggregated reporting table optimized for Grafana dashboard querying.
- `analytics_anomalies`: Flagged low-quality translations requiring engineering review.

---

## 9. PySpark Strategy
Local PySpark execution reading raw/interim datasets and PostgreSQL tables, performing:
- Null, empty string, and whitespace validation.
- Text length and token ratio computations.
- Weighted quality score formulation.
- Outlier detection via IQR / standard deviation boundaries on latency and length ratios.
- Aggregation across temporal (`date`), categorical (`source_language`, `target_language`, `style_option`, `provider`) dimensions.
- Batch write-back to PostgreSQL analytics tables via JDBC.

---

## 10. Gradio Strategy
Clean, single-page interface featuring:
- Source and Target language dropdowns.
- Source text area with character counter.
- "Translate" action button calling `TranslationService.translate(...)`.
- Interactive cards/radio to preview and select among candidate styles (Natural / Idiomatic, Formal / Context-aware, Literal).
- Instant feedback submission (Thumbs Up / Down or Good / Poor, Reason dropdown, text note).
- Complete isolation from provider-specific logic.

---

## 11. Translation Provider Abstraction Strategy
- `src/translation/service.py`: Orchestrates translation requests, timer measurements, error normalization, and database recording.
- `src/translation/providers/base.py`: Declares `BaseTranslationProvider` interface.
- `src/translation/providers/huggingface_provider.py`: Default provider using Hugging Face Inference Providers (`HF_TOKEN` with 'Make calls to Inference Providers' permission).
- `src/translation/providers/mock_provider.py`: Fast deterministic mock provider returning simulated styles for unit testing and offline development.
- `src/translation/providers/cohere_provider.py`: Optional future provider using Cohere API (`COHERE_API_KEY`).

---

## 12. Feedback Strategy
- Binary satisfaction: `GOOD` / `POOR`.
- Granular failure taxonomy for `POOR`:
  - `INCORRECT_MEANING`
  - `GRAMMAR`
  - `TOO_LITERAL`
  - `WRONG_CONTEXT`
  - `OTHER`
- Feeds PySpark anomaly tables and guides iterative prompt updates.

---

## 13. Grafana Strategy
Pre-configured Grafana instance provisioning PostgreSQL data source:
- **Core Panels**:
  - Daily translation volume & trends
  - Top language pairs
  - Average latency by language pair
  - Poor-quality reports & failure reason distribution
  - Quality score distribution
  - Recent flagged anomalies
- **Secondary Provider Panels**:
  - Translation volume by provider (`huggingface` vs `cohere` vs `mock`)
  - Average translation latency by provider
  - Poor-quality report rate by provider

---

## 14. Current Implementation Status
- **Current Phase**: **PHASE 4: Translation Abstraction & Core Engine**
- **Overall Status**: `PHASE 4 COMPLETED` (Pydantic DTOs, BaseTranslationProvider, MockTranslationProvider, HuggingFaceTranslationProvider, and TranslationService implemented and validated with 100% test pass rate).
- **Environment Status**: Virtual environment active, dependencies installed, `.env` configured with user HF_TOKEN.
- **Data Status**: 68,000 raw OPUS-100 records ingested.

---

## 15. Completed Tasks
- [x] Initialized workspace repository structure.
- [x] Defined complete documentation suite requirements.
- [x] Formulated core architecture and data flow blueprints.
- [x] Authored all required documentation files in `docs/`.
- [x] Created all Mermaid architecture and workflow diagrams in `docs/diagrams/`.
- [x] Created root `.env.example`, `.gitignore`, and `README.md`.
- [x] Created `requirements.txt` with pinned dependencies.
- [x] Initialized Python virtual environment `.venv` and verified core imports.
- [x] Ingested 68,000 baseline OPUS-100 records across 6 pairs in `data/raw/opus100/`.
- [x] Updated architectural foundation to make **Hugging Face Inference Providers** the default provider and **Cohere** an optional future provider.
- [x] Configured user's Hugging Face token in local `.env` (gitignored, securely stored).
- [x] Created `src/config.py` with typed Pydantic Settings.
- [x] Implemented `src/translation/models.py` (`TranslationRequestDTO`, `TranslationOptionDTO`, `TranslationResultDTO`).
- [x] Implemented `src/translation/providers/base.py` (`BaseTranslationProvider` interface).
- [x] Implemented `src/translation/providers/mock_provider.py` (offline deterministic testing provider).
- [x] Implemented `src/translation/providers/huggingface_provider.py` (Hugging Face Inference Providers integration with multi-style prompt and exponential retry).
- [x] Implemented `src/translation/service.py` (`TranslationService` provider-agnostic orchestrator with latency measurement).
- [x] Created `pytest.ini` and comprehensive unit tests in `tests/unit/test_translation_service.py` (all 7 tests passing).
- [x] Implemented `src/database/connection.py` with connection pooling, health checks, and schema initialization.
- [x] Implemented `src/database/repository.py` with transactional persistence for translations, options, feedback, and analytics marts.
- [x] Implemented `src/feedback/service.py` with taxonomy validation (`INCORRECT_MEANING`, `GRAMMAR`, `TOO_LITERAL`, `WRONG_CONTEXT`, `OTHER`).
- [x] Created `gradio_app/app.py` with multi-style translation cards, preferred variant selection, feedback controls, and session audit log.
- [x] Implemented `scripts/enrich_baseline.py` and generated 67,934 feature-engineered records in `data/interim/enriched_baseline/`.
- [x] Implemented `pyspark_jobs/etl_job.py` computing distributed multi-dimensional aggregates (date, pair, style, provider), p95 latency, quality score $Q$, and anomaly triage.
- [x] Configured Grafana datasource and dashboard provisioning in `grafana/provisioning/` with 8 panels.
- [x] Started containerized PostgreSQL 15 (`localhost:5435`) and Grafana 10 (`localhost:3000`) via `docker compose`.
- [x] Authored 25 comprehensive unit tests across database, feedback, Gradio UI, and translation service (all 25 passing).

---

## 16. Phased Implementation Roadmap
- [x] **Phase 1**: Documentation and architecture
- [x] **Phase 2**: Project skeleton and configuration
- [x] **Phase 3**: PostgreSQL database (Models, tables, connection engine, repository)
- [x] **Phase 4**: Translation abstraction (`TranslationService`, `BaseTranslationProvider`, DTOs)
- [x] **Phase 5**: Hugging Face provider (`HuggingFaceTranslationProvider`)
- [x] **Phase 6**: Mock provider (`MockTranslationProvider`)
- [x] **Phase 7**: Gradio UI (Interactive translation web interface)
- [x] **Phase 8**: Feedback system (Feedback ingestion and persistence)
- [x] **Phase 9**: OPUS-100 dataset ingestion (68,000 baseline records staged)
- [x] **Phase 10**: PySpark ETL (Cleaning, features, and Parquet staging)
- [x] **Phase 11**: Quality analytics (Quality scoring, aggregations & anomaly detection)
- [x] **Phase 12**: Grafana dashboards (Observability panels & datasource provisioning)
- [x] **Phase 13**: Testing (25/25 unit tests passing)
- [x] **Phase 14**: Dockerization (PostgreSQL & Grafana compose setup)
- [ ] **Phase 15**: Optional Cohere provider (Deferred / non-blocking)

---

## 17. Rules for Future AI Agents
1. **Never write code before checking this file.**
2. **Never import provider SDKs directly into UI or database layers.**
3. **Always preserve provider abstraction behind `TranslationService`.**
4. **Never hardcode API keys or tokens in code or documentation.**
5. **Whenever a task or phase is completed, update this document immediately.**
