# Configuration Management & Environment Variables
# Translation Quality Analytics & Continuous Improvement Platform

**Status**: Configuration Specification (Updated for Pluggable Provider Architecture)  
**Version**: 1.1.0  
**Phase**: Architecture & Documentation

---

## 1. Configuration Philosophy
All configuration parameters, credentials, and network endpoints are decoupled from application logic through environment variables, following the **Twelve-Factor App** methodology.

> **CRITICAL SECURITY DIRECTIVE:**  
> Real secrets, tokens (`HF_TOKEN`), and API keys (`COHERE_API_KEY`) must NEVER be committed to version control. 
> The repository includes a sanitized `.env.example` template with dummy values. The active `.env` file is excluded via `.gitignore`.

---

## 2. Configuration Parameters Catalog

| Variable Name | Required | Default Value | Description |
| :--- | :--- | :--- | :--- |
| **`TRANSLATION_PROVIDER`** | No | `huggingface` | Active provider: `huggingface` (Default), `cohere` (Optional), or `mock` (Testing) |
| **`HF_TOKEN`** | **If HF Active** | *None* | Hugging Face User Access Token (Perm: 'Make calls to Inference Providers') |
| **`HF_MODEL`** | No | `meta-llama/Llama-3.1-8B-Instruct` | Target model routed via Hugging Face Inference Providers |
| **`COHERE_API_KEY`** | **If Cohere Active**| *None* | Optional Cohere platform API key (only if `TRANSLATION_PROVIDER=cohere`) |
| **`COHERE_MODEL`** | No | `command-r` | Target Cohere multilingual model |
| **`POSTGRES_HOST`** | No | `localhost` | PostgreSQL server hostname |
| **`POSTGRES_PORT`** | No | `5432` | PostgreSQL server port |
| **`POSTGRES_DB`** | No | `translation_analytics` | Database name |
| **`POSTGRES_USER`** | No | `postgres` | Database admin / service username |
| **`POSTGRES_PASSWORD`**| No | `postgres` | Database user password |
| **`DATABASE_URL`** | No | `postgresql://postgres:postgres@localhost:5432/translation_analytics` | Full SQLAlchemy connection URI |
| **`GRAFANA_ADMIN_USER`**| No | `admin` | Initial Grafana admin username |
| **`GRAFANA_ADMIN_PASSWORD`**| No | `admin` | Initial Grafana admin password |
| **`GRADIO_SERVER_NAME`** | No | `127.0.0.1` | Host interface for Gradio web server |
| **`GRADIO_SERVER_PORT`** | No | `7860` | Network port for Gradio web server |
| **`SPARK_DRIVER_MEMORY`** | No | `4g` | Java heap allocation for PySpark driver |
| **`LOG_LEVEL`** | No | `INFO` | Application log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## 3. Provider Credential Isolation Rule

> **Important Operational Rule**:  
> Only the provider specified by `TRANSLATION_PROVIDER` needs to be configured for execution:
> - When `TRANSLATION_PROVIDER=huggingface`: Only `HF_TOKEN` is needed. `COHERE_API_KEY` can be omitted.
> - When `TRANSLATION_PROVIDER=mock`: No external tokens or internet access are required.
> - When `TRANSLATION_PROVIDER=cohere`: `COHERE_API_KEY` is required.

---

## 4. Python Configuration Loader Architecture

Configuration will be loaded and validated using **Pydantic Settings** (`src/config.py`):

```python
from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppConfig(BaseSettings):
    translation_provider: Literal["huggingface", "cohere", "mock"] = Field(
        default="huggingface", env="TRANSLATION_PROVIDER"
    )
    hf_token: Optional[str] = Field(default=None, env="HF_TOKEN")
    hf_model: str = Field(default="meta-llama/Llama-3.1-8B-Instruct", env="HF_MODEL")
    
    cohere_api_key: Optional[str] = Field(default=None, env="COHERE_API_KEY")
    cohere_model: str = Field(default="command-r", env="COHERE_MODEL")
    
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(default="translation_analytics", env="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", env="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", env="POSTGRES_PASSWORD")
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/translation_analytics", 
        env="DATABASE_URL"
    )

    grafana_admin_user: str = Field(default="admin", env="GRAFANA_ADMIN_USER")
    grafana_admin_password: str = Field(default="admin", env="GRAFANA_ADMIN_PASSWORD")
    
    gradio_server_name: str = Field(default="127.0.0.1", env="GRADIO_SERVER_NAME")
    gradio_server_port: int = Field(default=7860, env="GRADIO_SERVER_PORT")

    spark_driver_memory: str = Field(default="4g", env="SPARK_DRIVER_MEMORY")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
```
