# Internal Service & API Contract Design
# Translation Quality Analytics & Continuous Improvement Platform

**Status**: API Design Specification (Updated for Pluggable Provider Architecture)  
**Version**: 1.1.0  
**Phase**: Architecture & Documentation

---

## 1. Design Principles & Modularity
The platform is architected as a **modular Python monolith**. 
To avoid the overhead of orchestrating distributed microservices, internal modules communicate via typed Python interfaces using **Pydantic v2 Data Transfer Objects (DTOs)**.

If external HTTP REST consumption is required in the future, these service boundaries can be exposed via FastAPI with zero structural refactoring.

---

## 2. Core Service Contracts

### 2.1 Translation Service Contract (`src/translation/service.py`)

#### `translate()`
Dispatches text to the active provider (`HuggingFaceTranslationProvider` by default, `MockTranslationProvider` in testing, or optional `CohereTranslationProvider`), measures execution latency, and commits the transaction to the repository.

```python
class TranslationRequestDTO(BaseModel):
    source_text: str = Field(..., min_length=1, max_length=5000)
    source_language: str = Field(default="en", max_length=10)
    target_language: str = Field(..., max_length=10)
    requested_styles: list[str] = Field(default=["LITERAL", "NATURAL", "FORMAL"])

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

**Signature**:
```python
def translate(request: TranslationRequestDTO) -> TranslationResultDTO:
    """Dispatches multi-style translation via the configured provider and persists records."""
```

---

### 2.2 Provider Interface Contract (`src/translation/providers/base.py`)

```python
from abc import ABC, abstractmethod

class BaseTranslationProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the canonical provider name (e.g., 'huggingface', 'cohere', 'mock')."""
        pass

    @abstractmethod
    def generate_translations(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
        styles: list[str]
    ) -> tuple[list[TranslationOptionDTO], Optional[float]]:
        """
        Executes model inference and returns candidate style options and confidence score.
        """
        pass
```

---

### 2.3 Feedback Service Contract (`src/feedback/service.py`)

#### `record_feedback()`
Validates, links, and persists user feedback against an option.

```python
class FeedbackSubmissionDTO(BaseModel):
    option_id: UUID
    rating: Literal["GOOD", "POOR"]
    reason: Optional[Literal[
        "INCORRECT_MEANING", 
        "GRAMMAR", 
        "TOO_LITERAL", 
        "WRONG_CONTEXT", 
        "OTHER"
    ]] = None
    comments: Optional[str] = Field(default=None, max_length=1000)

class FeedbackResponseDTO(BaseModel):
    feedback_id: UUID
    option_id: UUID
    rating: str
    reason: Optional[str]
    created_at: datetime
    status: Literal["RECORDED", "UPDATED"]

def record_feedback(submission: FeedbackSubmissionDTO) -> FeedbackResponseDTO:
    """Validates user feedback and updates or inserts into database."""
```

---

### 2.4 Translation History Contract (`src/database/repository.py`)

```python
class HistoryFilterDTO(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    target_language: Optional[str] = None
    provider: Optional[str] = None

def get_recent_translations(filters: HistoryFilterDTO) -> list[TranslationResultDTO]:
    """Returns paginated historical translations."""
```

---

### 2.5 Analytics Summary Contract (`src/analytics/service.py`)

```python
class QualityOverviewDTO(BaseModel):
    total_volume: int
    average_latency_ms: float
    global_downvote_rate: float
    top_language_pairs: list[dict]
    provider_breakdown: dict[str, int]
    last_batch_run: Optional[datetime]

def get_quality_overview() -> QualityOverviewDTO:
    """Retrieves high-level KPI summary from PostgreSQL analytics mart."""
```

---

## 3. Error Handling & Standard Domain Exceptions

```python
class DomainException(Exception):
    def __init__(self, message: str, code: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.status_code = status_code

class TranslationProviderException(DomainException):
    """Raised when an external translation provider fails."""
    pass

class ProviderAuthenticationException(DomainException):
    """Raised when API token is invalid or missing."""
    pass

class DatabaseUnavailableException(DomainException):
    """Raised when PostgreSQL connection cannot be acquired."""
    pass
```
