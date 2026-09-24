# Data Flow Architecture & Lifecycle
# Translation Quality Analytics & Continuous Improvement Platform

**Status**: Data Flow Specification (Updated for Multi-Provider Architecture)  
**Version**: 1.1.0  
**Phase**: Architecture & Documentation

---

## 1. End-to-End Data Lifecycle Overview

The platform operates across two synchronized data pathways:
1. **Interactive Real-Time Transaction Flow**: Handles live user translation requests, variant selection, and feedback capture via Gradio and `TranslationService` (delegating to Hugging Face, Cohere, or MockProvider) into PostgreSQL.
2. **Batch Big Data Analytics & Staging Flow**: Stages external baseline corpus (OPUS-100), ingests live PostgreSQL data, runs PySpark feature transformations and quality classifications, and writes analytical marts for Grafana.

---

## 2. Interactive Real-Time Data Flow

### 2.1 Live Request & Feedback Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Gradio as Gradio Interface
    participant Service as TranslationService
    participant Provider as Active Provider\n(HF / Mock / Cohere)
    participant DB as PostgreSQL
    participant Feedback as Feedback Handler

    User->>Gradio: Enter text, pick Source (en) & Target (e.g., hi)
    User->>Gradio: Click "TRANSLATE NOW"
    Gradio->>Service: translate(text, "en", "hi")
    
    activate Service
    Service->>Provider: generate_translations(prompt)
    activate Provider
    Provider-->>Service: Return styles (Literal, Natural, Formal) + confidence
    deactivate Provider
    
    Service->>DB: INSERT into translations (request_id, provider, text, latency, etc.)
    Service->>DB: INSERT into translation_options (candidate_ids, styles, texts)
    Service-->>Gradio: Return candidate options & request_id
    deactivate Service

    Gradio-->>User: Display options for comparison
    User->>Gradio: Select preferred option (e.g., "Natural")
    Gradio->>DB: UPDATE translation_options SET user_selected = true

    opt Submit Feedback
        User->>Gradio: Click "POOR", pick "TOO_LITERAL", enter note
        Gradio->>Feedback: submit_feedback(option_id, "POOR", "TOO_LITERAL")
        Feedback->>DB: INSERT into feedback (id, option_id, rating, reason)
        Feedback-->>Gradio: Acknowledge feedback saved
        Gradio-->>User: Display feedback confirmation alert
    end
```

---

## 3. Batch Big Data Analytics Flow

### 3.1 Batch ETL Pipeline Flow

```mermaid
flowchart TD
    subgraph StagingPhase ["Phase 1: Baseline Corpus Staging"]
        O100[(OPUS-100 Corpus\n68,000 Ingested Pairs)]
        STAGE_SCRIPT[Enrichment Engine: Add Latency, Style, Feedback]
        PARQUET[(Staged Parquet Baseline)]
        
        O100 --> STAGE_SCRIPT --> PARQUET
    end

    subgraph ApplicationExtract ["Phase 2: Live Operational Extraction"]
        PG_TRANS[(PostgreSQL: translations\nWith Provider Column)]
        PG_OPT[(PostgreSQL: translation_options)]
        PG_FB[(PostgreSQL: feedback)]
        JDBC_EXTRACT[PySpark JDBC Extractor]
        
        PG_TRANS & PG_OPT & PG_FB --> JDBC_EXTRACT
    end

    subgraph SparkProcessing ["Phase 3: PySpark Distributed Transformations"]
        UNION[Unified DataFrame Ingestion]
        CLEAN[Text Cleansing & Token Normalization]
        FEAT[Feature Engineering: Lengths, Ratios, Word Counts]
        HEURISTIC[Quality Scoring & Outlier Detection]
        AGG[Dimensional Aggregation: Date, Pair, Style, Provider]
        
        PARQUET --> UNION
        JDBC_EXTRACT --> UNION
        UNION --> CLEAN --> FEAT --> HEURISTIC --> AGG
    end

    subgraph AnalyticsEgress ["Phase 4: Analytics Storage & Visualization"]
        PG_METRICS[(PostgreSQL: analytics_daily_metrics)]
        PG_ANOM[(PostgreSQL: analytics_anomalies)]
        GRAFANA[Grafana Dashboards]
        
        AGG -->|Batch Insert / Upsert| PG_METRICS
        HEURISTIC -->|Filter flagged outliers| PG_ANOM
        PG_METRICS -->|SQL Direct Queries| GRAFANA
        PG_ANOM -->|SQL Alerting & Tables| GRAFANA
    end
```

---

## 4. Stage-by-Stage Data Transformation Matrix

| Stage | Input Data | Operation | Output Data | Storage Target |
| :--- | :--- | :--- | :--- | :--- |
| **0. Raw Ingest** | OPUS-100 raw archives | Filter to target pairs (`en-hi`, `en-fr`, `en-es`, `en-de`, `en-bn`, `en-ja`) | Clean parallel text | `data/raw/opus100/` (68k rows) |
| **1. Baseline Staging** | Raw OPUS-100 | Inject realistic operational telemetry (latencies, candidate styles, baseline ratings) with `provider='opus100_baseline'` | Enriched baseline records | `data/interim/enriched_baseline/` (Parquet) |
| **2. Spark Ingest** | Staged Parquet + PostgreSQL tables | Schema unification, timestamp casting | Raw Spark DataFrame | In-memory Spark DataFrame |
| **3. Clean & Validate** | Raw Spark DataFrame | Filter nulls, trim whitespace, deduplicate IDs, validate ISO language codes | Sanitized DataFrame | Spark memory |
| **4. Feature Engineering** | Sanitized DataFrame | Compute `char_len_src`, `char_len_tgt`, `word_cnt_src`, `word_cnt_tgt`, $Ratio = \frac{len(tgt)}{len(src)}$ | Enriched Features DataFrame | Spark memory |
| **5. Quality Scoring** | Enriched Features DataFrame | Calculate weighted $Q$-score, assign quality categories (`EXCELLENT`, `GOOD`, `NEEDS_REVIEW`, `POOR`), flag anomalies | Scored DataFrame | Spark memory |
| **6. Aggregation** | Scored DataFrame | Group by `(metric_date, provider, source_lang, target_lang, style_option)` computing volume, percentiles, downvote rate | Aggregated Metrics DataFrame | Spark memory |
| **7. Egress** | Aggregated & Outlier DataFrames | JDBC write with connection pooling | Relational Analytics Mart | PostgreSQL `analytics_*` |
| **8. Visualization** | PostgreSQL `analytics_*` | Time-series and categorical SQL queries | Interactive charts, alerts | Grafana |
