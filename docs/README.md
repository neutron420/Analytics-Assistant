# Translation Quality Analytics & Continuous Improvement Platform
## Documentation Index & Architecture Guide

Welcome to the comprehensive technical documentation for the **Translation Quality Analytics & Continuous Improvement Platform**.

---

## 1. Documentation Index

### Core Architecture & Foundations
- **[PROJECT_MEMORY.md](./PROJECT_MEMORY.md)**: **Living source of truth**. Must be consulted before making any code or architecture changes.
- **[REQUIREMENTS.md](./REQUIREMENTS.md)**: Comprehensive functional (FR-01 to FR-15) and non-functional requirements.
- **[ARCHITECTURE.md](./ARCHITECTURE.md)**: High-level architectural layout, provider abstraction, protocols, and fail-safes.
- **[SYSTEM_DESIGN.md](./SYSTEM_DESIGN.md)**: Deep-dive component decomposition, module contracts, and partitioning.
- **[DATA_FLOW.md](./DATA_FLOW.md)**: Detailed transaction lifecycle and batch big-data journey.
- **[DECISIONS.md](./DECISIONS.md)**: Formal Architecture Decision Records (ADR-001 through ADR-011).

### Data Engineering & Analytics
- **[DATASET.md](./DATASET.md)**: OPUS-100 corpus subsetting (68,000 baseline records), enrichment, and strict 3-tier separation.
- **[DATABASE.md](./DATABASE.md)**: PostgreSQL 3NF schema, provider attribution, indexes, constraints, and data dictionaries.
- **[PYSPARK_ETL.md](./PYSPARK_ETL.md)**: Distributed PySpark pipeline specifications, feature engineering, and JDBC write-back.
- **[QUALITY_ANALYTICS.md](./QUALITY_ANALYTICS.md)**: Deterministic heuristic scoring model, thresholds, and anomaly detection rules.

### Application Services & User Interface
- **[TRANSLATION_SERVICE.md](./TRANSLATION_SERVICE.md)**: Translation provider abstraction, Hugging Face Inference Providers (Default), MockProvider (Testing), and Cohere (Optional).
- **[GRADIO_UI.md](./GRADIO_UI.md)**: Zero-JS Python-native Gradio interface specifications, wireframes, and event wiring.
- **[FEEDBACK_SYSTEM.md](./FEEDBACK_SYSTEM.md)**: Human-in-the-loop defect taxonomy and the prompt engineering continuous improvement loop.
- **[API_DESIGN.md](./API_DESIGN.md)**: Internal Python service contracts, Pydantic DTO models, and error structures.

### Infrastructure, Security & Operations
- **[GRAFANA.md](./GRAFANA.md)**: PostgreSQL data source provisioning, dashboard panel queries, and alerting thresholds.
- **[DOCKER.md](./DOCKER.md)**: Docker Compose orchestration for PostgreSQL and Grafana.
- **[CONFIGURATION.md](./CONFIGURATION.md)**: Environment variable definitions and Twelve-Factor configuration loading.
- **[SECURITY.md](./SECURITY.md)**: Secret isolation, token protection (`HF_TOKEN`, `COHERE_API_KEY`), and prompt injection mitigations.
- **[TESTING.md](./TESTING.md)**: Test pyramid, pytest suites, and edge case verification catalog.

### Governance & Execution Roadmap
- **[IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)**: Strict 15-phase roadmap with dependencies and exit criteria (Cohere non-blocking in Phase 15).
- **[DEVELOPMENT_RULES.md](./DEVELOPMENT_RULES.md)**: 20 mandatory engineering standards for developers and AI agents.
- **[diagrams/](./diagrams/README.md)**: Standalone Mermaid architectural and workflow diagrams.

---

## 2. System Status & Governance Notice

> **STATUS**: **Phase 1 (Architecture & Documentation - Updated) Active**  
> All documentation files in this directory are the authoritative source of truth. Application code implementation must not begin without alignment with these specifications and explicit approval.
