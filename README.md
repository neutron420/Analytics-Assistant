# Translation Quality Analytics & Continuous Improvement Platform

[![Architecture Status](https://img.shields.io/badge/Architecture-Provider--Agnostic-success.svg)](./docs/ARCHITECTURE.md)
[![Default Provider](https://img.shields.io/badge/Default%20Provider-Hugging%20Face%20Inference%20Providers-ffd21e.svg)](./docs/TRANSLATION_SERVICE.md)
[![Optional Provider](https://img.shields.io/badge/Optional%20Provider-Cohere%20API-6b46c1.svg)](./docs/TRANSLATION_SERVICE.md)
[![Data Engine](https://img.shields.io/badge/ETL-Apache%20Spark%203.4+-E25A1C.svg)](./docs/PYSPARK_ETL.md)
[![Persistence](https://img.shields.io/badge/Database-PostgreSQL%2015-336791.svg)](./docs/DATABASE.md)
[![Monitoring](https://img.shields.io/badge/Observability-Grafana-F46800.svg)](./docs/GRAFANA.md)

---

## 1. Project Overview & Problem Statement

Production machine translation systems face severe observability gaps. Generic LLM or machine translation APIs operate as black boxes, lacking systematic tracking of latency profiles, length distortion, and user satisfaction across diverse language pairs. When end users encounter unnatural or erroneous translations, qualitative feedback rarely connects back to structured big data pipelines. Furthermore, tightly coupling application code to a single commercial LLM vendor creates vendor lock-in and billing vulnerabilities.

The **Translation Quality Analytics & Continuous Improvement Platform** bridges this divide by combining:
- **Pluggable Translation Architecture**: A provider-agnostic `TranslationService` using **Hugging Face Inference Providers** as the default engine, with a deterministic **MockProvider** for testing and **Cohere** as an optional alternative.
- **Multi-Style Generation**: Translates into Literal, Natural / Idiomatic, and Formal / Context-aware variants in a single round-trip.
- **Human-in-the-Loop Feedback**: Granular user evaluation and failure categorization in a Python-native Gradio interface.
- **Relational Integrity**: Transactional persistence of requests, candidate options, provider attribution, and user feedback in PostgreSQL.
- **Distributed Big Data Engineering**: PySpark batch pipelines that clean, transform, and evaluate 68,000 baseline records from OPUS-100 alongside live application telemetry.
- **Operational Observability**: Pre-aggregated Grafana dashboards visualizing volume trends, latency percentiles, defect distributions, flagged quality anomalies, and provider breakdowns.
- **Continuous Improvement Loop**: A feedback-driven mechanism to systematically refine prompt instructions and system guidelines based on empirical defect patterns.

---

## 2. Key Features

- **Provider-Agnostic Design**: Seamlessly switch between Hugging Face Inference Providers, Cohere, or MockProvider via `.env` without modifying UI or analytics code.
- **Multi-Style Translation**: Generates Literal, Natural / Idiomatic, and Formal / Context-aware styles.
- **Zero-JavaScript Frontend**: Clean, responsive Gradio web interface eliminates split-stack frontend complexities.
- **Linguistic Defect Taxonomy**: Granular feedback options for negative ratings (`INCORRECT_MEANING`, `GRAMMAR`, `TOO_LITERAL`, `WRONG_CONTEXT`, `OTHER`).
- **Distributed Quality Analytics**: PySpark ETL computes character lengths, token ratios, latency buckets, and composite quality scores.
- **Automated Anomaly Detection**: Identifies severe length truncations, runaway hallucinations, and latency outliers.
- **Observability Dashboards**: Pre-provisioned Grafana dashboards tracking volume, language-pair latency matrix, downvote percentages, provider comparisons, and quality distributions.

---

## 3. High-Level Architecture

```
User (Browser) <---> Gradio Web App (:7860) <---> TranslationService
                                                         |
                                     +-------------------+-------------------+
                                     |                   |                   |
                                     v                   v                   v
                             Hugging Face (Default)    Cohere (Optional)   Mock (Testing)
                                     |
                                     v
                             PostgreSQL (:5432)
                          [translations / feedback]
                                     |
                                     v (JDBC Extract)
OPUS-100 Baseline -------> PySpark Batch ETL & Quality Engine
(68,000 Ingested Pairs)              |
                                     v (JDBC Write)
                             PostgreSQL (:5432)
                          [analytics_daily_metrics / anomalies]
                                     |
                                     v
                             Grafana Dashboards (:3000)
```

For complete architectural details, see **[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)** and **[docs/SYSTEM_DESIGN.md](./docs/SYSTEM_DESIGN.md)**.

---

## 4. Technology Stack

| Layer | Component | Description |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ | Unified language across web UI, backend services, and Spark jobs |
| **User Interface** | Gradio | Clean Python-native web application (no React/Next.js) |
| **Default AI Provider** | Hugging Face Inference Providers | Primary development provider (`meta-llama/Llama-3.1-8B-Instruct`) |
| **Optional Provider** | Cohere API | Pluggable alternative (`command-r`), non-blocking |
| **Testing Provider** | Mock Translation Provider | Fast, offline deterministic generator for unit testing |
| **Relational Storage** | PostgreSQL 15 | Transactional operational store and analytics marts |
| **Big Data Engine** | Apache Spark (PySpark 3.4+) | Distributed batch data cleaning, feature derivation, and scoring |
| **Observability** | Grafana | Pre-provisioned operational metrics and anomaly dashboards |
| **Containerization** | Docker & Docker Compose | Local container orchestration for PostgreSQL and Grafana |
| **Host Environment** | Windows 11 + WSL2 (Ubuntu) | Local, reproducible development environment |

---

## 5. Dataset Strategy: OPUS-100 & 3-Tier Separation

The platform stages a balanced baseline of **68,000 parallel pairs** from **OPUS-100** across six prioritized English-centric pairs:
- English $\to$ Hindi (`en-hi`) — 12,000 pairs
- English $\to$ Spanish (`en-es`) — 12,000 pairs
- English $\to$ French (`en-fr`) — 12,000 pairs
- English $\to$ German (`en-de`) — 12,000 pairs
- English $\to$ Bengali (`en-bn`) — 10,000 pairs
- English $\to$ Japanese (`en-ja`) — 10,000 pairs

### Strict Data Separation:
1. **Base Corpus Data**: Provided by OPUS-100 (`source_text`, `translated_text`, `source_language`, `target_language`).
2. **Application Metadata**: Generated at runtime (`request_id`, `provider`, `translation_time_ms`, `confidence_score`, `style_option`, `user_selected`, `feedback_rating`, `feedback_reason`, `created_at`).
3. **Derived Analytics Features**: Computed in PySpark (`char_lengths`, `word_counts`, `length_ratio`, `quality_score`, `anomaly_flag`).

For complete dataset design, see **[docs/DATASET.md](./docs/DATASET.md)**.

---

## 6. End-to-End Workflows

### 6.1 Interactive Translation & Feedback Workflow
1. User enters text up to 5,000 characters and selects target language in Gradio.
2. `TranslationService` dispatches prompt to the active provider (Hugging Face by default) and measures latency.
3. Three translation options (Literal, Natural, Formal) are presented to the user.
4. User selects their preferred style and optionally submits `GOOD` or `POOR` feedback with failure reason.
5. All actions are persisted into PostgreSQL tables (`translations`, `translation_options`, `feedback`).

### 6.2 Big Data & Analytics Workflow
1. Historical staged baseline data (Parquet) and live PostgreSQL tables are ingested into PySpark.
2. Cleansing rules filter nulls, strip whitespace, and deduplicate.
3. Feature engineering derives character lengths, word counts, and length ratios.
4. Quality engine computes composite quality score ($Q$) and flags anomalies.
5. PySpark writes daily aggregations and outlier records into PostgreSQL.
6. Grafana queries pre-aggregated tables to visualize operational health and trends.

---

## 7. Phased Development Roadmap

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase 1** | Documentation and Architecture | **COMPLETED** |
| **Phase 2** | Project Skeleton and Configuration | **COMPLETED** |
| **Phase 3** | PostgreSQL Database (Schema & connection engine) | PLANNED |
| **Phase 4** | Translation Abstraction (`TranslationService`, `BaseTranslationProvider`) | PLANNED |
| **Phase 5** | Hugging Face Provider (Default provider via Inference Providers) | PLANNED |
| **Phase 6** | Mock Provider (For testing & offline development) | PLANNED |
| **Phase 7** | Gradio UI (Interactive translation interface) | PLANNED |
| **Phase 8** | Feedback System (Rating controls & defect taxonomy) | PLANNED |
| **Phase 9** | OPUS-100 Dataset Ingestion (68k baseline staged) | **COMPLETED** |
| **Phase 10** | PySpark ETL (Cleaning, features, JDBC egress) | PLANNED |
| **Phase 11** | Quality Analytics (Quality scoring & anomaly detection) | PLANNED |
| **Phase 12** | Grafana Dashboards (Provisioning & visualization panels) | PLANNED |
| **Phase 13** | Testing (Unit, integration, and Spark tests) | PLANNED |
| **Phase 14** | Dockerization (Full stack verification) | PLANNED |
| **Phase 15** | Optional Cohere Provider (Non-blocking extension) | PLANNED |
