# Architecture Diagrams & Visual Workflows
# Translation Quality Analytics & Continuous Improvement Platform

This directory contains standalone Mermaid diagram definitions (`.mmd`) representing the complete architectural, lifecycle, and operational models for the platform.

---

## Diagram Index

| File | Diagram Title | Description |
| :--- | :--- | :--- |
| **[`system_architecture.mmd`](./system_architecture.mmd)** | System Architecture | End-to-end component topology spanning UI, Provider Abstraction, Database, Spark, and Grafana. |
| **[`data_flow.mmd`](./data_flow.mmd)** | End-to-End Data Flow | Data progression from raw ingestion to staging, processing, storage, and visualization with provider dimension. |
| **[`database_er.mmd`](./database_er.mmd)** | Database Entity-Relationship | 3NF operational tables and analytics summary data marts with `provider` tracking. |
| **[`translation_sequence.mmd`](./translation_sequence.mmd)** | Translation Request Sequence | Call sequence between User, Gradio, TranslationService, pluggable Provider, and PostgreSQL. |
| **[`feedback_loop.mmd`](./feedback_loop.mmd)** | Feedback & Quality Loop | Flow from user defect submission through Spark aggregation to prompt engineering recovery. |
| **[`pyspark_etl_pipeline.mmd`](./pyspark_etl_pipeline.mmd)** | PySpark Processing Pipeline | Multi-stage batch execution model (Ingest, Clean, Feature Engineering, Scoring, Egress). |
| **[`grafana_analytics_flow.mmd`](./grafana_analytics_flow.mmd)** | Grafana Analytics Flow | PostgreSQL datasource integration with dashboard panels, provider analytics, and alerts. |

---

## Rendering Instructions
These diagrams are formatted in standard GitHub Flavored Mermaid syntax. They can be rendered:
- Natively in any Markdown previewer supporting Mermaid (VS Code, GitHub, Antigravity IDE).
- Using the Mermaid Live Editor (`https://mermaid.live`).
- Programmatically using `mmdc` (Mermaid CLI).
