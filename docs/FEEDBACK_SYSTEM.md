# Human Feedback System & Quality Improvement Loop
# Translation Quality Analytics & Improvement Platform

**Status**: Feedback System Specification  
**Version**: 1.0.0  
**Phase**: Phase 0 (Architecture & Documentation)

---

## 1. Overview & Feedback Philosophy
Human-in-the-loop (HITL) feedback is the vital bridge connecting raw AI generation with operational data engineering. The feedback subsystem enables users to rate generated candidate translations, systematically categorize quality defects, and feed that signal into both batch analytics and iterative prompt refinement.

---

## 2. Feedback Taxonomy & Schema

### 2.1 Feedback Ratings
- **`GOOD` (Positive)**: The translation accurately preserves the source meaning, sounds natural/appropriate for the selected style, and has no grammatical defects.
- **`POOR` (Negative)**: The translation contains factual, grammatical, syntactic, or tonal errors.

### 2.2 Granular Defect Taxonomy (For `POOR` Ratings)

| Defect Code | Classification Label | Description / Linguistic Manifestation |
| :--- | :--- | :--- |
| **`INCORRECT_MEANING`** | Semantic Distortion | Severe mistranslation; inverted meaning, hallucinations, or omitted core clauses. |
| **`GRAMMAR`** | Syntactic / Grammar Defect | Broken agreement (gender, number, tense), incorrect particles, or malformed conjugation. |
| **`TOO_LITERAL`** | Unnatural / Calque | Word-for-word translation that violates target language idioms or natural phrasing. |
| **`WRONG_CONTEXT`** | Tonal / Register Inaccuracy | Using informal phrasing in formal settings (e.g., Japanese Keigo / Hindi honorific errors). |
| **`OTHER`** | Miscellaneous / Unspecified | Punctuation anomalies, untranslated loanwords, or special character corruption. |

---

## 3. End-to-End Feedback Lifecycle

```
[ User Reviews Translation Variant in Gradio ]
                       |
                       v
[ User Selects 'POOR' + 'TOO_LITERAL' + Adds Comment ]
                       |
                       v
[ FeedbackHandler Validates & Persists to PostgreSQL `feedback` Table ]
                       |
                       v
[ PySpark Daily Batch Job Extracts `feedback` Joined with `translations` ]
                       |
                       +---> Computes `poor_feedback_rate` per Language Pair
                       +---> Aggregates Defect Reason Distribution
                       +---> Flags Downvoted Candidates into `analytics_anomalies`
                       |
                       v
[ Grafana Dashboard Renders Live Downvote Rate & Defect Heatmaps ]
                       |
                       v
[ Continuous Improvement Loop: Prompt & Configuration Tuning ]
```

---

## 4. Continuous Improvement: Prompt Tuning vs. Model Fine-Tuning

> **CRITICAL ARCHITECTURAL DISTINCTION:**
> We explicitly reject false claims that user feedback "automatically fine-tunes the foundational translation model." 
> Fine-tuning large foundational LLMs (such as models served via Hugging Face or Cohere) on sporadic feedback introduces severe catastrophic forgetting, extreme training compute costs, and latency regressions.

Instead, this platform implements a realistic, auditable **Feedback-Driven Prompt & Configuration Improvement Loop**:

```
+-----------------------------------------------------------------------------------+
| 1. ANALYTICAL DETECTION (Grafana & PySpark)                                       |
| - Grafana identifies an elevated downvote rate in English -> Hindi (e.g., 28%).   |
| - Defect taxonomy reveals 70% of downvotes are tagged `TOO_LITERAL`.             |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 2. AUDIT & ROOT CAUSE TRIAGE                                                      |
| - Linguistics engineer queries `analytics_anomalies` filtering on `TOO_LITERAL`.  |
| - Inspects source idioms (e.g., "spill the beans", "break a leg").                |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 3. SYSTEMATIC PROMPT ENHANCEMENT                                                  |
| - Engineer updates `src/translation/prompts.py` for target `hi`.                  |
| - Adds few-shot idiomatic guidelines and explicit instructions for colloquialism. |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 4. VERIFICATION & MEASURED RECOVERY                                               |
| - Next week's PySpark batch job tracks `poor_feedback_rate` on `en-hi`.            |
| - Grafana demonstrates downvote rate dropping from 28% to 8%.                      |
+-----------------------------------------------------------------------------------+
```

---

## 5. Storage Integrity & Deduplication Rules
- **One Feedback Per Option**: A user can update or submit one feedback rating per candidate option. Duplicate submissions within the same session execute an `UPDATE` on the existing `feedback` row rather than inserting redundant rows.
- **Cascading Integrity**: If a translation request is pruned or purged, associated feedback records cascade delete cleanly via foreign key constraints.
