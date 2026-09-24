# Architecture Decision Records (ADRs)
# Translation Quality Analytics & Continuous Improvement Platform

**Status**: Active Architecture Decisions (Updated for Pluggable Provider Architecture)  
**Version**: 1.1.0  
**Phase**: Architecture & Documentation

---

## Index of Architecture Decision Records

| ADR ID | Title | Status | Date |
| :--- | :--- | :--- | :--- |
| **ADR-001** | Use Gradio as the Primary User Interface | Accepted | 2026-09-24 |
| **ADR-002** | Use OPUS-100 as the Baseline Translation Corpus | Accepted | 2026-09-24 |
| **ADR-003** | Ingest a Manageable Subset (50k–100k) of OPUS-100 | Accepted | 2026-09-24 |
| **ADR-004** | Use PySpark for Distributed ETL & Quality Heuristics | Accepted | 2026-09-24 |
| **ADR-005** | Use PostgreSQL for Transactional Persistence & Data Marts | Accepted | 2026-09-24 |
| **ADR-006** | Use Grafana for Operational Observability & Analytics | Accepted | 2026-09-24 |
| **ADR-007** | Use Docker Compose for Supporting Infrastructure Services | Accepted | 2026-09-24 |
| **ADR-008** | Disallow Google Colab as a Mandatory Runtime Dependency | Accepted | 2026-09-24 |
| **ADR-009** | Use External LLM / Translation Providers Rather Than Training from Scratch | Accepted | 2026-09-24 |
| **ADR-010** | Distinguish Prompt/Configuration Improvement from Neural Fine-Tuning | Accepted | 2026-09-24 |
| **ADR-011** | Use Hugging Face Inference Providers as Default Provider with Pluggable Abstraction | Accepted | 2026-09-24 |

---

## ADR-001: Use Gradio as the Primary User Interface
- **Context**: The project requires a clean, responsive web interface for translation requests, variant selection, and quality feedback submission.
- **Decision**: Build the UI exclusively using Gradio Blocks in Python. Do not build a React, Next.js, or Vite frontend.
- **Reason**: Gradio allows seamless Python integration with backend services, eliminates JavaScript build toolchains, and minimizes frontend maintenance overhead while providing all necessary interactive widgets.
- **Alternatives**: React SPA, Next.js with TailwindCSS, Streamlit, HTML/Jinja templates.
- **Consequences**: Fast development and zero JS build dependencies, but less custom micro-interaction styling than a custom React application.

---

## ADR-002: Use OPUS-100 as the Baseline Translation Corpus
- **Context**: The platform needs a realistic, large-scale multilingual baseline dataset to demonstrate big data ETL and analytics before months of live user interaction accumulate.
- **Decision**: Select OPUS-100 as the foundational open translation corpus.
- **Reason**: OPUS-100 is an established academic benchmark covering all target language pairs (`en-hi`, `en-es`, `en-fr`, `en-de`, `en-bn`, `en-ja`).
- **Alternatives**: WMT benchmark corpora, Tatoeba, Common Crawl parallel data.
- **Consequences**: High-quality parallel sentence pairs, but lacks operational metadata, requiring synthetic telemetry enrichment during staging.

---

## ADR-003: Ingest a Manageable Subset (50k–100k) of OPUS-100
- **Context**: Full OPUS-100 spans tens of millions of records across 100 languages, requiring hundreds of gigabytes of disk and distributed clusters.
- **Decision**: Ingest a balanced subset of 50,000 to 100,000 records (68,000 ingested in Phase 2) centered on 6 English-centric language pairs.
- **Reason**: Enables thorough big data processing validation on standard developer hardware (Windows/WSL2) without disk saturation or OutOfMemory errors.
- **Alternatives**: Ingesting the full 55M corpus; using a trivial toy dataset of 500 rows.
- **Consequences**: Realistic data volume for Spark performance benchmarking without requiring cloud infrastructure.

---

## ADR-004: Use PySpark for Distributed ETL & Quality Heuristics
- **Context**: Scalable translation quality analytics requires processing millions of historical tokens, computing length ratios, percentiles, and outlier anomalies.
- **Decision**: Use PySpark (local mode) for batch ETL, feature engineering, and aggregations.
- **Reason**: PySpark provides industry-standard distributed computing paradigms (partitioning, shuffles, lazy evaluation) that directly scale from local development to multi-node clusters.
- **Alternatives**: Pure Pandas, DuckDB, Polars.
- **Consequences**: Demonstrates big data engineering competency; requires Java runtime (OpenJDK 17) on the development host.

---

## ADR-005: Use PostgreSQL for Transactional Persistence & Data Marts
- **Context**: The system must persist real-time translation requests, multi-variant candidates, user feedback ratings, provider attribution, and Spark aggregated summary metrics.
- **Decision**: Deploy PostgreSQL 15+ via Docker.
- **Reason**: ACID compliance, strong relational integrity (foreign keys and cascading deletes), rich JSON support, and native integration with Grafana.
- **Alternatives**: MongoDB, SQLite, MySQL.
- **Consequences**: Requires managing relational database schemas and connection pooling.

---

## ADR-006: Use Grafana for Operational Observability & Analytics
- **Context**: Engineering and product teams require operational dashboards to track translation volume, latency percentiles, language-pair quality degradation, provider mix, and user defect reports.
- **Decision**: Use Grafana connected directly to PostgreSQL analytics tables.
- **Reason**: Standardized, production-grade observability platform with rich charting capabilities, alerting rules, and automated provisioning via YAML/JSON.
- **Alternatives**: Custom web dashboards inside Gradio, Matplotlib static plots, Metabase.
- **Consequences**: Clear decoupling of visualization from application code; requires running a Grafana container.

---

## ADR-007: Use Docker Compose for Supporting Infrastructure Services
- **Context**: Setting up PostgreSQL and Grafana manually across diverse host operating systems creates configuration drift and dependency friction.
- **Decision**: Use Docker Compose to manage PostgreSQL and Grafana containers.
- **Reason**: One-command infrastructure orchestration, reproducible networking, and persistent volume management.
- **Alternatives**: Manual native Windows/Linux service installations.
- **Consequences**: Requires Docker Desktop or Docker engine running on the host machine.

---

## ADR-008: Disallow Google Colab as a Mandatory Runtime Dependency
- **Context**: Cloud notebook environments introduce state loss, ephemeral filesystems, and connectivity friction with local databases.
- **Decision**: The platform must execute entirely within the local development environment (Windows/WSL2).
- **Reason**: Guarantees reproducibility, code versioning, and unified local networking between Gradio, PostgreSQL, and PySpark.
- **Alternatives**: Google Colab notebooks with ngrok tunnels.
- **Consequences**: All dependencies must be configured locally.

---

## ADR-009: Use External LLM / Translation Providers Rather Than Training from Scratch
- **Context**: Building and training state-of-the-art multilingual neural machine translation models requires millions of dollars in GPU compute and months of training.
- **Decision**: Leverage external foundational multilingual LLMs and translation APIs via structured prompt engineering.
- **Reason**: Focuses engineering efforts on the end-to-end data pipeline, quality analytics, feedback loops, and observability rather than model training.
- **Alternatives**: Training a custom Transformer with PyTorch, fine-tuning mBART/NLLB locally.
- **Consequences**: Requires an external API key/token and internet connectivity for real-time translation calls.

---

## ADR-010: Distinguish Prompt/Configuration Improvement from Neural Fine-Tuning
- **Context**: Feedback systems frequently claim to "automatically fine-tune the model," which is technically inaccurate and unfeasible for foundation LLM APIs.
- **Decision**: Explicitly define the continuous improvement loop as **Feedback-Driven Prompt & Configuration Optimization**.
- **Reason**: Architectural honesty and operational feasibility. PySpark and Grafana isolate linguistic defects (e.g., idiomatic failure in `en-hi`), allowing targeted prompt updates and parameter adjustments.
- **Alternatives**: Claiming unverified LoRA fine-tuning; ignoring feedback completely.
- **Consequences**: Clear, auditable, and realistic improvement workflow without unexpected retraining costs.

---

## ADR-011: Use Hugging Face Inference Providers as Default Provider with Pluggable Abstraction
- **Context**: Initial project development should not depend on Cohere production billing or credit card verification hurdles. Furthermore, hardcoding client logic to a single proprietary provider creates architectural fragility and vendor lock-in.
- **Decision**: Implement a provider-agnostic `TranslationService` facade and make **Hugging Face Inference Providers** the default provider (`TRANSLATION_PROVIDER=huggingface`). Retain **Cohere** as an optional future provider (`TRANSLATION_PROVIDER=cohere`), and provide a **MockTranslationProvider** (`TRANSLATION_PROVIDER=mock`) for offline testing.
- **Reason**: 
  - Hugging Face provides a unified inference router with accessible development allowances and community-supported models.
  - Pluggable strategy pattern decouples the Gradio UI, feedback loop, database schema, and PySpark ETL from any specific provider SDK.
  - Allows seamless switching or multi-provider evaluation without rewriting application or pipeline code.
  - Does not require a paid production Cohere setup for initial development.
- **Alternatives Considered & Rejected**:
  - *Making Cohere mandatory for initial development*: Rejected because production billing onboarding blocks development progress.
  - *Directly replacing Cohere with hardcoded Hugging Face calls*: Rejected because hardcoding any single provider repeats vendor lock-in.
- **Consequences**: Clean architectural decoupling via `BaseTranslationProvider`; developers configure `HF_TOKEN` locally with 'Make calls to Inference Providers' permission.
