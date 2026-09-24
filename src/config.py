"""
Application Configuration
Translation Quality Analytics & Continuous Improvement Platform

Loads and validates environment variables using Pydantic Settings.
"""

from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    # Active Translation Provider
    translation_provider: Literal["huggingface", "cohere", "mock"] = Field(
        default="huggingface", validation_alias="TRANSLATION_PROVIDER"
    )

    # Hugging Face Inference Providers Configuration (DEFAULT)
    hf_token: Optional[str] = Field(default=None, validation_alias="HF_TOKEN")
    hf_model: str = Field(default="meta-llama/Llama-3.1-8B-Instruct", validation_alias="HF_MODEL")

    # Cohere API Configuration (OPTIONAL / FUTURE)
    cohere_api_key: Optional[str] = Field(default=None, validation_alias="COHERE_API_KEY")
    cohere_model: str = Field(default="command-r", validation_alias="COHERE_MODEL")

    # PostgreSQL Relational Database Configuration
    postgres_host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    postgres_db: str = Field(default="translation_analytics", validation_alias="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", validation_alias="POSTGRES_PASSWORD")
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/translation_analytics",
        validation_alias="DATABASE_URL"
    )

    # Grafana Observability Settings
    grafana_admin_user: str = Field(default="admin", validation_alias="GRAFANA_ADMIN_USER")
    grafana_admin_password: str = Field(default="admin", validation_alias="GRAFANA_ADMIN_PASSWORD")

    # Gradio Web Server Settings
    gradio_server_name: str = Field(default="127.0.0.1", validation_alias="GRADIO_SERVER_NAME")
    gradio_server_port: int = Field(default=7860, validation_alias="GRADIO_SERVER_PORT")

    # PySpark & Logging Settings
    spark_driver_memory: str = Field(default="4g", validation_alias="SPARK_DRIVER_MEMORY")
    spark_executor_memory: str = Field(default="2g", validation_alias="SPARK_EXECUTOR_MEMORY")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Singleton instance
config = AppConfig()
