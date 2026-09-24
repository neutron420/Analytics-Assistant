# System Design Document
# Translation Quality Analytics & Continuous Improvement Platform

**Status**: Design Specification (Updated for Pluggable Provider Architecture)  
**Version**: 1.1.0  
**Phase**: Architecture & Documentation

---

## 1. System Overview & Decomposition
The Translation Quality Analytics & Continuous Improvement Platform is composed of six distinct subsystems, designed for high cohesion, loose coupling, and complete provider independence.

```
                    +------------------------------------+
                    |         Gradio Presentation        |
                    +------------------------------------+
                                      |
                                      v
                    +------------------------------------+
                    |         TranslationService         |
                    +------------------------------------+
                      /             |                  \
                     v              v                   v
+-----------------------+  +------------------+  +--------------------+
|  Provider Abstraction |  | Feedback Handler |  | Storage Repository |
|  - Hugging Face (Def) |  +------------------+  +--------------------+
|  - Mock (Testing)     |                               |
|  - Cohere (Optional)  |                               v
+-----------------------+                 +---------------------------+
                                          | PostgreSQL Relational DB  |
                                          +---------------------------+
                                                        ^
                                                        | (JDBC read/write)
                                          +---------------------------+
+-----------------------+                 | PySpark Batch Processing  |
| OPUS-100 Staging Area | --------------> | ETL & Heuristic Engine    |
+-----------------------+                 +---------------------------+
                                                        |
                                                        v
                                          +---------------------------+
                                          |  Grafana Visual Dashboards|
                                          +---------------------------+
```

---

## 2. Subsystem Decomposition and Module Contracts

### 2.1 Translation Subsystem (`src/translation/`)
- **`TranslationService`** (`src/translation/service.py`): The single public entry point for translation generation.
  - *Contract*:
    ```python
    def translate(
        source_text: str,
        source_lang: str,
        target_lang: str,
        styles: list[str] = ["LITERAL", "NATURAL", "FORMAL"]
    ) -> TranslationResultDTO:
        ...
    ```
  - *Responsibilities*: Validates payloads, routes requests to the configured provider, measures round-trip latency, handles errors, normalizes output into `TranslationResultDTO`, and triggers database persistence.
- **Provider Sub-package** (`src/translation/providers/`):
  - `base.py`: Defines the `BaseTranslationProvider` abstract base class with method `generate_translations(...)`.
  - `huggingface_provider.py`: **Default provider**. Interacts with Hugging Face Inference Providers via `HF_TOKEN`.
  - `mock_provider.py`: **Testing provider**. Deterministic offline generator for unit tests and CI.
  - `cohere_provider.py`: **Optional provider**. Pluggable Cohere API adaptor activated via `TRANSLATION_PROVIDER=cohere`.

### 2.2 Feedback Subsystem (`src/feedback/`)
- **`FeedbackManager`**: Validates and persists user feedback.
  - *Contract*:
    ```python
    def submit_feedback(
        option_id: UUID,
        rating: Literal["GOOD", "POOR"],
        reason: Optional[FeedbackReason] = None,
        comments: Optional[str] = None
    ) -> FeedbackRecordDTO:
        ...
    ```
  - *Validation Rules*: If `rating == "POOR"`, a valid `reason` is recorded (defaulting to `OTHER` if unspecified).

### 2.3 Persistence Subsystem (`src/database/`)
- Uses **SQLAlchemy 2.0+** ORM for type safety and connection pooling.
- **`TranslationRepository`**: Encapsulates transactional CRUD operations on `translations` (including `provider` column), `translation_options`, and `feedback`.
- **`AnalyticsRepository`**: Provides read/write interfaces for aggregated summary tables (`analytics_daily_metrics`, `analytics_anomalies`).

### 2.4 Dataset Staging Subsystem (`src/etl/staging/`)
- Baseline corpus (OPUS-100 68,000 pairs across 6 language pairs) is staged into `data/raw/opus100/`.
- An enrichment script (`scripts/enrich_baseline.py`) enriches raw rows with simulated operational metadata (latencies, candidate styles, feedback ratings) with `provider='opus100_baseline'`.
- Serializes staged records into columnar Parquet format partitioned by `target_language`.

### 2.5 PySpark Analytics Subsystem (`pyspark_jobs/`)
- Standalone Spark application written for Spark 3.4+.
- Sub-modules:
  - **`IngestionStage`**: Reads staged Parquet files and PostgreSQL operational records.
  - **`TransformationStage`**: Performs text tokenization, string length calculation, language tag standardizing.
  - **`QualityEngine`**: Calculates the weighted Quality Score ($Q$) and detects anomaly vectors (length distortion, high latency).
  - **`AggregationStage`**: Groups by `(metric_date, provider, source_lang, target_lang, style)` computing `p50_latency`, `p95_latency`, `poor_feedback_rate`, `avg_quality_score`.
  - **`EgressStage`**: Writes analytical frames back to PostgreSQL with idempotent upserts.

### 2.6 Observability Subsystem (`grafana/`)
- Pre-packaged Grafana container configured via Docker Compose.
- Automated provisioning of the PostgreSQL datasource via `grafana/provisioning/datasources/postgres.yaml`.
- Automated dashboard provisioning via `grafana/provisioning/dashboards/translation_quality_dashboard.json`.

---

## 3. Data Storage & Partitioning Strategy

### 3.1 Relational Tables (PostgreSQL)
- **`translations`**: Primary operational table. Keyed on `UUIDv4`. Indexed on `created_at` (B-tree), `(source_lang, target_lang)` composite index, and `provider`.
- **`translation_options`**: Child table with foreign key `translation_id REFERENCES translations(id) ON DELETE CASCADE`.
- **`feedback`**: Child table with foreign key `option_id REFERENCES translation_options(id)`.
- **`analytics_daily_metrics`**: Analytical table indexed on `(metric_date, source_lang, target_lang)` and `provider` for ultra-fast Grafana range queries.

### 3.2 File-Based Analytics Staging (Parquet)
```
data/
├── raw/
│   └── opus100/
│       ├── manifest.json
│       ├── en-hi/train.jsonl
│       ├── en-es/train.jsonl
│       ├── en-fr/train.jsonl
│       ├── en-de/train.jsonl
│       ├── en-bn/train.jsonl
│       └── en-ja/train.jsonl
├── interim/
│   └── enriched_baseline/
│       ├── target_language=hi/
│       ├── target_language=es/
│       ├── target_language=fr/
│       ├── target_language=de/
│       ├── target_language=bn/
│       └── target_language=ja/
└── processed/
    └── spark_warehouse/
```

---

## 4. Concurrency, Throughput, and Scaling
- **Gradio & Web Traffic**: Gradio runs with an asynchronous Python backend. In-flight translation calls to external providers execute with non-blocking I/O or background threads.
- **PySpark Batch Scaling**: Executes locally with `spark.master = "local[4]"` and `spark.driver.memory = "4g"`.
- **Stateless Architecture**: Translation providers are stateless, making the application trivially scale horizontally.
