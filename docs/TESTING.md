# Testing & Quality Assurance Strategy
# Translation Quality Analytics & Continuous Improvement Platform

**Status**: Testing Specification (Updated for Pluggable Provider Testing)  
**Version**: 1.1.0  
**Phase**: Architecture & Documentation

---

## 1. Testing Philosophy & Test Pyramid
Quality assurance is structured across four layers to guarantee reliability from low-level algorithms to user-facing workflows and big data transformations.

```
                   / \
                  /   \
                 / E2E \       Gradio Smoke & Workflow Tests
                /-------\
               / Integr. \     PostgreSQL Repository & Spark JDBC Tests
              /-----------\
             / Data Quality\   PySpark Data Cleansing & Schema Tests
            /---------------\
           /   Unit Tests    \ Schemas, Heuristics, Mock Provider Abstraction
          /-------------------\
```

---

## 2. Test Suite Categorization & Provider Abstraction

### 2.1 Unit Tests (`tests/unit/`)
- **Offline & Token-Free Standard**: Unit tests must NEVER make live external API calls or require network connectivity.
- **Provider Mocking**: All unit tests evaluate `TranslationService` using `MockTranslationProvider` (`TRANSLATION_PROVIDER=mock`).
- **Key Suites**:
  - `test_schemas.py`: Verifies Pydantic DTO models enforce length constraints, UUID parsing, and enum validations.
  - `test_provider_abstraction.py`: Verifies that `TranslationService` correctly instantiates and switches between `MockTranslationProvider` and `HuggingFaceTranslationProvider` based on configuration.
  - `test_mock_provider.py`: Verifies `MockTranslationProvider` returns valid Literal, Natural, and Formal variants with expected schema keys.
  - `test_quality_heuristics.py`: Verifies Quality Score ($Q$) deterministic calculations, boundary conditions, and category assignments.
  - `test_prompts.py`: Verifies prompt construction across language pairs and styles.

### 2.2 Integration Tests (`tests/integration/`)
- **Target**: Service interactions with external dependencies (Hugging Face mock / test credentials, PostgreSQL).
- **Key Suites**:
  - `test_translation_service.py`: Tests end-to-end multi-style generation, latency tracking, and error handling through `TranslationService`.
  - `test_hf_provider.py`: Validates `HuggingFaceTranslationProvider` response parsing and retry behavior using recorded network fixtures (`responses` or `vcrpy`).
  - `test_feedback_service.py`: Verifies database commits and updates on user ratings.
  - `test_database_repository.py`: Verifies CRUD operations, cascading deletes, and transaction rollbacks against PostgreSQL.
  - *(Deferred)*: `test_cohere_provider.py` will be added in Phase 15.

### 2.3 PySpark Data Quality Tests (`tests/spark/`)
- **Target**: PySpark data pipelines, feature engineering, and aggregations.
- **Key Suites**:
  - `test_spark_cleansing.py`: Verifies null filtering, whitespace stripping, and deduplication logic against synthetic DataFrames.
  - `test_spark_features.py`: Verifies character length, word count, and length ratio calculations.
  - `test_spark_anomaly_detection.py`: Verifies truncation flags and extreme latency threshold detections.

### 2.4 Gradio UI Smoke Tests (`tests/ui/`)
- **Target**: UI component instantiation and callback registration.
- **Key Suites**:
  - `test_gradio_callbacks.py`: Asserts that UI block event handlers (`translate_btn.click`, `feedback_btn.click`) bind properly to backend functions with `MockTranslationProvider`.

---

## 3. Critical Edge Cases Catalog

| Test Case ID | Subsystem | Edge Case Scenario | Expected System Behavior |
| :--- | :--- | :--- | :--- |
| **EC-01** | UI / Translation | Empty or whitespace-only source text | Immediate UI warning; no provider invocation. |
| **EC-02** | UI / Translation | Oversized text (>5,000 characters) | UI truncation alert; rejected before provider dispatch. |
| **EC-03** | Translation | Target language unsupported (e.g., `xx`) | Validation error raised; clear error message returned. |
| **EC-04** | Translation | Provider returns HTTP 429 (Rate Limit) | Retries with exponential backoff up to 3 times; if unrecovered, user-friendly alert shown. |
| **EC-05** | Translation | Provider returns malformed non-JSON | Robust regex JSON extractor recovers candidate styles; logs parsing warning. |
| **EC-06** | Translation | Negative or zero latency measured | Sanitized to minimum floor value (1ms); prevents division-by-zero. |
| **EC-07** | Feedback | Feedback submitted without valid translation ID | Rejected with `400 Bad Request` validation error. |
| **EC-08** | Feedback | User submits `POOR` without choosing a reason | Defaults gracefully to `OTHER` defect code. |
| **EC-09** | Feedback | Duplicate feedback submitted on same option | Updates existing feedback row rather than inserting duplicate record. |
| **EC-10** | Database | PostgreSQL connection dropped during write | User still receives translation; error logged to local dead-letter queue. |
| **EC-11** | PySpark ETL | Dataset contains corrupt JSON or missing columns | Malformed rows quarantined to error partition; pipeline execution succeeds. |
| **EC-12** | PySpark ETL | Zero-character source text slips through | Handled cleanly; avoided `ZeroDivisionError` in length ratio calculation via `nullif()`. |

---

## 4. Test Execution Commands
```bash
# Run offline unit tests (uses MockTranslationProvider)
pytest tests/unit/ -v

# Run integration tests against active local database
pytest tests/integration/ -v

# Run PySpark data quality tests
pytest tests/spark/ -v

# Run entire test suite with coverage
pytest --cov=src --cov=pyspark_jobs tests/
```
