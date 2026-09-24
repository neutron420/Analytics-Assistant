# Translation Service & Provider Abstraction
# Translation Quality Analytics & Continuous Improvement Platform

**Status**: Service Specification (Updated for Pluggable Provider Architecture)  
**Version**: 1.1.0  
**Phase**: Architecture & Documentation

---

## 1. Overview & Service Responsibilities
The **Translation Service** (`src/translation/service.py`) acts as the provider-agnostic engine for generating translation variants. It decouples the user-facing Gradio interface from underlying LLM and translation APIs through a pluggable provider strategy.

### Core Responsibilities:
1. **Request Intake & Validation**: Receives source text, source language, target language, and requested styles.
2. **Provider Resolution**: Instantiates or selects the configured translation provider based on `TRANSLATION_PROVIDER` in environment configuration.
3. **Latency Measurement**: Accurately measures round-trip inference duration using high-resolution monotonic clocks (`time.perf_counter_ns`).
4. **Multi-Style Normalization**: Ensures every response contains normalized candidate options (Literal, Natural / Idiomatic, Formal / Context-aware).
5. **Error Normalization & Resilience**: Translates provider-specific exceptions (rate limits, network timeouts, invalid tokens) into unified domain exceptions.
6. **Consistent Internal Response Format**: Emits standardized `TranslationResultDTO` records to downstream consumers and persistence repositories.

---

## 2. Provider Abstraction Architecture

```
                    +------------------------------------+
                    |         TranslationService         |
                    |      (src/translation/service.py)  |
                    +------------------------------------+
                                      |
                                      v
                    +------------------------------------+
                    |      BaseTranslationProvider       |
                    |    (src/translation/providers/     |
                    |              base.py)              |
                    +------------------------------------+
                         /            |            \
                        /             |             \
                       v              v              v
+-------------------------+  +-----------------+  +----------------------+
|  HuggingFaceProvider    |  |  MockProvider   |  |    CohereProvider    |
|       [DEFAULT]         |  |    [TESTING]    |  |  [OPTIONAL / FUTURE] |
|                         |  |                 |  |                      |
|  - Uses HF Inference    |  |  - Deterministic|  |  - Uses Cohere API   |
|    Providers            |  |    offline data |  |  - Enabled via       |
|  - Auth: HF_TOKEN       |  |  - Fast (<5ms)  |  |    COHERE_API_KEY    |
|  - Perm: Make calls to  |  |  - For tests/CI |  |  - No billing needed |
|    Inference Providers  |  |    & UI dev     |  |    for initial dev   |
+-------------------------+  +-----------------+  +----------------------+
```

---

## 3. Provider Implementations

### 3.1 `HuggingFaceTranslationProvider` (DEFAULT)
- **Role**: Primary provider for development and production inference.
- **Integration**: Leverages the **Hugging Face Inference Providers** router (via `huggingface_hub` InferenceClient or direct HTTPS REST).
- **Authentication**:
  - Configured via environment variable `HF_TOKEN`.
  - Required User Access Token Permission: **"Make calls to Inference Providers"**.
  - *Explicit Non-Requirement*: Does NOT require or use "Inference Endpoints" or "Manage Inference Endpoints" permissions.
- **Usage & Pricing Model**:
  - Hugging Face Inference Providers provides free-tier credits / monthly community usage allowances for open-weights multilingual models (e.g., Llama-3-Instruct, Mistral, Qwen, or dedicated translation models).
  - Usage beyond free allowances is subject to provider-dependent hourly/token pricing.
  - The provider is not assumed to be permanently free or unlimited; client-side quota and error handling are enforced.

### 3.2 `MockTranslationProvider` (TESTING / LOCAL DEV)
- **Role**: Deterministic generator for automated unit tests, UI smoke testing, CI pipelines, and offline development.
- **Behavior**:
  - Returns structured, realistic candidate translations without making network requests.
  - Operates with near-zero latency (~2ms).
  - Guarantees 100% test reproducibility without external API token dependencies.

### 3.3 `CohereTranslationProvider` (OPTIONAL / FUTURE)
- **Role**: Optional alternative provider for multi-style translation.
- **Activation**:
  - Enabled simply by setting `TRANSLATION_PROVIDER=cohere` and `COHERE_API_KEY=<secret>` in `.env`.
  - Architecturally supported through the common provider interface, but **NOT required** for initial project development.
  - No billing setup is required to run or evaluate this platform.

---

## 4. Multi-Style Translation Strategy

The platform produces three distinct translation styles:
1. **Literal / Direct**: Word-for-word syntactic mapping faithful to source sentence order; ideal for linguistic inspection and academic reference.
2. **Natural / Idiomatic**: Fluent phrasing adhering to target native speaker idioms and colloquial cadence.
3. **Formal / Context-aware**: Grammatically elevated, polite phrasing suited for professional, legal, or governmental contexts.

### Standardized System Prompt Schema:
```
You are an expert multilingual translation engine.
Translate the text enclosed in <source_text> from {source_language} to {target_language}.

Return a valid JSON object matching this schema:
{
  "translations": [
    {
      "style": "LITERAL",
      "text": "<direct, syntax-preserving translation>"
    },
    {
      "style": "NATURAL",
      "text": "<fluent, idiomatic everyday translation>"
    },
    {
      "style": "FORMAL",
      "text": "<polite, professional, context-appropriate translation>"
    }
  ],
  "confidence": 0.95
}
```

---

## 5. Normalized Internal Response Format

All providers map raw model outputs into a unified data structure:

```python
class TranslationOptionDTO(BaseModel):
    option_id: UUID
    style_option: Literal["LITERAL", "NATURAL", "FORMAL"]
    translated_text: str
    confidence_score: Optional[float] = None
    user_selected: bool = False

class TranslationResultDTO(BaseModel):
    request_id: UUID
    provider: Literal["huggingface", "cohere", "mock"]
    source_text: str
    source_language: str
    target_language: str
    translation_time_ms: int
    status: Literal["COMPLETED", "FAILED", "TIMEOUT"]
    options: list[TranslationOptionDTO]
    created_at: datetime
```

---

## 6. Error Handling & Resilience
- **Retry Mechanism**: Exponential backoff with jitter on HTTP 429 (Rate Limit) and HTTP 503 (Service Unavailable) up to 3 attempts.
- **Fail-Safe Fallbacks**: If JSON parsing fails, a regex fallback extractor parses candidate blocks before raising `TranslationParserException`.
- **Domain Exceptions**:
  - `ProviderAuthenticationError`: Token missing or invalid.
  - `ProviderQuotaExceededError`: Usage limit reached.
  - `UnsupportedLanguageError`: Target language code not supported.
  - `TranslationTimeoutError`: Provider latency exceeded timeout threshold (default 10s).
