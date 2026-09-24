# Requirements Specification
# Translation Quality Analytics & Continuous Improvement Platform

**Status**: Baseline Draft (Updated for Pluggable Provider Architecture)  
**Version**: 1.1.0  
**Phase**: Architecture & Documentation

---

## 1. Introduction and Objectives
The objective of the **Translation Quality Analytics & Continuous Improvement Platform** is to deliver a reliable, observable translation system combining:
1. Real-time multi-style neural translation via an extensible translation provider abstraction (**Hugging Face Inference Providers** by default, with **MockProvider** for testing and **Cohere** as an optional future provider).
2. Intuitive web-based user selection and quality feedback (via Gradio UI).
3. ACID persistence of translation metadata, provider attributes, and user ratings (PostgreSQL).
4. Large-scale data engineering and heuristic quality evaluation (Apache Spark / PySpark).
5. Observability and performance tracking dashboards (Grafana).

---

## 2. Functional Requirements (FR)

| ID | Title | Description | Priority |
| :--- | :--- | :--- | :--- |
| **FR-01** | **Source Text Ingestion** | The system shall provide an input mechanism allowing users to submit arbitrary source text (up to 5,000 characters) for translation. | High |
| **FR-02** | **Source Language Selection** | The system shall allow users to explicitly specify the source language (defaulting to English `en`). | High |
| **FR-03** | **Target Language Selection** | The system shall allow users to select from supported target languages: Hindi (`hi`), Bengali (`bn`), French (`fr`), German (`de`), Spanish (`es`), and Japanese (`ja`). | High |
| **FR-04** | **Provider-Agnostic Translation Dispatch** | The system shall dispatch translation requests through an internal `TranslationService` to the configured translation provider (**Hugging Face Inference Providers** by default, **Cohere** as an optional alternative, or **MockProvider** for testing). | High |
| **FR-05** | **Multi-Style Translation Generation** | The system shall produce at least three distinct translation style variants per request: **Literal / Direct**, **Natural / Idiomatic**, and **Formal / Context-aware**. | High |
| **FR-06** | **Translation Selection** | The user interface shall enable the user to view all generated variants and explicitly select their preferred output. | High |
| **FR-07** | **Quality Feedback Capture** | The user interface shall provide binary feedback controls (`GOOD` / `POOR`) on any translation variant. | High |
| **FR-08** | **Feedback Categorization** | When a user submits `POOR` feedback, the system shall provide a categorized reason picker (`INCORRECT_MEANING`, `GRAMMAR`, `TOO_LITERAL`, `WRONG_CONTEXT`, `OTHER`) and an optional notes field. | High |
| **FR-09** | **Request & Options Persistence** | The system shall persist every translation request, source text, target language, provider tag (`huggingface`, `cohere`, `mock`), response latency, and generated options into PostgreSQL. | High |
| **FR-10** | **Feedback Persistence** | The system shall record user feedback, associated translation ID, selected variant ID, timestamp, and feedback reason in PostgreSQL. | High |
| **FR-11** | **Batch Dataset Ingestion & Staging** | The system shall ingest an OPUS-100 translation corpus subset (~50k–100k pairs), normalize text, and stage enriched baseline telemetry for analytics. | High |
| **FR-12** | **PySpark Quality & Metric Computation** | The PySpark batch pipeline shall compute character lengths, token ratios, latency percentiles, composite quality scores, and anomaly classifications across language pairs and providers. | High |
| **FR-13** | **Grafana Observability Integration** | The system shall expose aggregated relational tables enabling Grafana to visualize volume, latency trends, failure rates, quality distributions, and provider comparisons. | High |
| **FR-14** | **Language-Pair Dimensional Analytics** | The system shall aggregate and report all metrics segmented by language pair (`en-hi`, `en-es`, `en-fr`, `en-de`, `en-bn`, `en-ja`). | High |
| **FR-15** | **Quality Anomaly Detection** | The PySpark pipeline shall identify and flag translations with extreme length discrepancies (e.g., potential truncation or hallucination) or repeated user downvotes. | Medium |

---

## 3. Non-Functional Requirements (NFR)

### 3.1 Performance
- **NFR-P1 (Interactive Latency)**: External translation provider multi-variant generation and rendering in Gradio should complete within an average of 1,500ms to 3,500ms (depending on network and provider response times). Mock provider generation shall complete in under 50ms.
- **NFR-P2 (ETL Throughput)**: The PySpark batch job must process 100,000 translation records in under 3 minutes on a standard developer workstation (4 cores, 16GB RAM).
- **NFR-P3 (Dashboard Query Speed)**: Pre-aggregated Grafana analytics queries over historical rows must execute in under 250ms via indexed SQL tables.

### 3.2 Scalability & Extensibility
- **NFR-S1 (Stateless Services)**: The Gradio UI and translation dispatch modules must remain stateless, allowing horizontal replication.
- **NFR-S2 (Provider Decoupling)**: Adding a new translation provider (e.g., Anthropic, OpenAI, local Ollama) must require only implementing the internal `BaseTranslationProvider` interface without altering UI, database, or analytics layers.
- **NFR-S3 (Modular Big Data Pipelines)**: The PySpark batch jobs must execute identically on local developer workstations or multi-node clusters without code refactoring.

### 3.3 Reliability and Fault Tolerance
- **NFR-R1 (API Resilience)**: Provider adaptors must implement exponential backoff retry logic (up to 3 retries) for handling rate limits (HTTP 429) or transient network timeouts (HTTP 503).
- **NFR-R2 (Database Fallback)**: If PostgreSQL persistence fails temporarily, the user interface must still return the generated translation to the user while logging the database write error.

### 3.4 Observability and Monitoring
- **NFR-O1 (Structured Logging)**: All application services must log in structured JSON format, recording `timestamp`, `request_id`, `provider`, `event_type`, `latency_ms`, and `status`.
- **NFR-O2 (Visual Dashboards)**: Key operational indicators (throughput, error rates, feedback distribution, p95 latency, provider volume) must be visually accessible on Grafana.

### 3.5 Security and Data Privacy
- **NFR-SEC1 (Secret Management)**: API tokens (`HF_TOKEN`, `COHERE_API_KEY`) and database credentials must strictly reside in environment variables (`.env`) and never be committed to source control or logged.
- **NFR-SEC2 (Input Sanitization)**: Text inputs must be sanitized against prompt injection and malicious control characters before downstream processing.
- **NFR-SEC3 (Parameterized Queries)**: All database interactions must use SQLAlchemy ORM or parameterized SQL queries to prevent SQL injection.

### 3.6 Data Quality & Reproducibility
- **NFR-DQ1 (Idempotent Pipelines)**: The PySpark ETL job must be fully idempotent; running the job multiple times over the same input snapshot must yield identical output data without duplicate rows.
- **NFR-DQ2 (Deterministic Metrics)**: Quality formulas and classification thresholds must be version-controlled and deterministically verifiable via automated unit tests.
