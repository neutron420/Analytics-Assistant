# Development Rules & Engineering Standards
# Translation Quality Analytics & Continuous Improvement Platform

**Status**: Governance & Developer Guidelines (Updated for Multi-Provider Architecture)  
**Version**: 1.1.0  
**Phase**: Architecture & Documentation

> **MANDATORY POLICY FOR ALL ENGINEERS & AI AGENTS:**  
> The following rules are binding across all subsequent development phases. Any pull request or automated code contribution that violates these rules must be rejected.

---

## 1. Architectural Integrity & Scope Discipline

1. **Rule 1 — Source of Truth**: Before undertaking any feature work, architectural adjustment, or debugging task, every AI agent or human developer MUST read `PROJECT_MEMORY.md` and the specific module documentation in `docs/`.
2. **Rule 2 — Module Documentation First**: Read the relevant module document (e.g., `PYSPARK_ETL.md` or `TRANSLATION_SERVICE.md`) before writing or altering code for that subsystem.
3. **Rule 3 — Pluggable Provider Abstraction**: All translation requests must pass through `TranslationService`. The Gradio UI, feedback layer, database repository, and PySpark jobs must NEVER import or depend directly on Hugging Face, Cohere, or any external LLM SDK.
4. **Rule 4 — Default Provider is Hugging Face**: Hugging Face Inference Providers is the default provider for development. Cohere is an optional future provider. Unit tests must use `MockTranslationProvider`.
5. **Rule 5 — No Mandatory Billing / Blockers**: Development must never be blocked on commercial billing setups. If external provider access is unavailable, development proceeds with `MockTranslationProvider`.
6. **Rule 6 — No JavaScript Frontends**: Do NOT create React, Next.js, Vue, Vite, or another standalone frontend.
7. **Rule 7 — Gradio is the Interface**: Gradio is the sole user-facing interface for translation, candidate selection, and feedback submission.
8. **Rule 8 — Local Reproducibility (No Colab Dependency)**: All scripts, ingestion jobs, and PySpark pipelines must execute locally on the Windows/WSL2 developer environment. Google Colab is explicitly NOT a required dependency.

---

## 2. Data Engineering & Integrity Standards

9. **Rule 9 — PySpark Reproducibility**: PySpark jobs must be deterministic, idempotent, and capable of executing locally without cluster orchestration overhead.
10. **Rule 10 — Never Commit Secrets**: Never commit tokens (`HF_TOKEN`), API keys (`COHERE_API_KEY`), database passwords, or private keys to Git. Always use `.env` and verify `.gitignore`.
11. **Rule 11 — Never Invent Dataset Fields**: Do NOT claim that OPUS-100 contains telemetry, provider, or feedback fields.
12. **Rule 12 — Strict Data Tier Separation**: Maintain strict separation across:
    - *Base Corpus Data* (`source_text`, `translated_text`, language codes)
    - *Application Metadata* (`request_id`, `provider`, `latency_ms`, `confidence`, `style`, `feedback`)
    - *Derived Analytics Features* (`lengths`, `ratios`, `quality_score`, `anomaly_flag`)
13. **Rule 13 — Normalized Database Schema**: Keep PostgreSQL operational tables normalized to 3NF. Only create summary tables for performance-critical analytical queries (e.g., Grafana marts).

---

## 3. Code Quality & Maintenance Discipline

14. **Rule 14 — Simplicity Over Cleverness**: Prefer simple, explicit, readable code over abstract metaprogramming or unnecessary layers of indirection.
15. **Rule 15 — Synchronize Documentation**: Whenever an implementation detail alters a schema, endpoint signature, or configuration key, update the corresponding documentation file immediately.
16. **Rule 16 — Update Project Memory on Phase Completion**: Every completed phase in `IMPLEMENTATION_PLAN.md` must update Sections 14, 15, and 16 of `PROJECT_MEMORY.md`.
17. **Rule 17 — No Silent Architectural Drift**: Never quietly bypass an ADR or modify an established architectural pattern without updating `DECISIONS.md`.
18. **Rule 18 — Dependency Minimalism**: Before adding a package to `requirements.txt`, verify that the standard library or an already-installed dependency cannot satisfy the requirement.
19. **Rule 19 — Production-Quality Python**: Follow PEP 8 guidelines, utilize Python type hints (`typing`), and use Pydantic models for data validation across boundaries.
20. **Rule 20 — Explicit Error Handling & Testing**: Catch specific exceptions; never use bare `except:` clauses. Always test with `MockTranslationProvider` so unit tests require zero network calls or credentials.
