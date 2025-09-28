"""
Configuration management for Research Copilot
"""
import os
from typing import Dict, List, Optional

from pydantic_settings import BaseSettings
from pydantic import field_validator, Field


class LangfuseSettings(BaseSettings):
    """Langfuse configuration settings"""

    public_key: Optional[str] = None
    secret_key: Optional[str] = None
    host: str = "https://cloud.langfuse.com"
    enabled: bool = True
    flush_at: int = 15
    flush_interval: float = 1.0
    max_retries: int = 3
    timeout: int = 30
    debug: bool = False

    class Config:
        case_sensitive = False


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Application Settings
    environment: str = "development"
    debug: bool = False
    app_name: str = "Research Copilot"
    app_version: str = "0.1.0"

    # Database Configuration
    database_url: str
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "research_copilot"
    db_user: str = "user"
    db_password: str = "password"

    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # OpenSearch Configuration
    opensearch_url: str = "http://localhost:9200"
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_index_name: str = "research_papers"
    opensearch_user: Optional[str] = None
    opensearch_password: Optional[str] = None

    # OpenRouter Configuration
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    deepseek_model: str = "deepseek/deepseek-chat"

    # Embedding Configuration
    embedding_provider: str = "gemini"  # "openrouter" or "gemini"
    embedding_model: str = "openai/text-embedding-ada-002"
    embedding_dimension: int = 1536
    embedding_batch_size: int = 100
    embedding_max_retries: int = 3
    embedding_retry_delay: float = 1.0
    embedding_cache_ttl: int = 86400  # 24 hours

    # Gemini Configuration
    gemini_api_key: str = ""

    # JWT Authentication
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Security
    secret_key: str
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Rate Limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10

    # Monitoring
    prometheus_port: int = 8001
    metrics_enabled: bool = True

    # External Services
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)

    # File Upload
    max_upload_size: int = 10485760  # 10MB
    allowed_extensions: List[str] = ["pdf", "txt", "md"]

    # Cache Settings
    cache_ttl: int = 3600  # 1 hour
    cache_max_size: int = 1000

    # Search Settings
    search_max_results: int = 100
    search_hybrid_weight_text: float = 0.7
    search_hybrid_weight_vector: float = 0.3

    # RAG Settings
    rag_default_model: str = "deepseek/deepseek-chat"
    rag_max_context_docs: int = 5
    rag_context_window_size: int = 8192
    rag_default_temperature: float = 0.7
    rag_default_max_tokens: int = 1000
    rag_cache_ttl: int = 1800  # 30 minutes
    rag_batch_max_queries: int = 10

    # Rate Limiting for RAG
    rag_rate_limit_requests_per_minute: int = 5
    rag_rate_limit_streaming_requests_per_minute: int = 3
    rag_rate_limit_batch_max_queries_per_minute: int = 10

    # Data Ingestion Settings
    # arXiv API Configuration
    arxiv_base_url: str = "http://export.arxiv.org/api/query"
    arxiv_rate_limit_delay: float = 3.0  # seconds between requests
    arxiv_timeout_seconds: int = 30
    arxiv_max_results_per_request: int = 2000
    arxiv_max_retries: int = 3
    arxiv_retry_delay_base: float = 1.0
    arxiv_default_category: str = "cs.AI"  # Default category for ingestion
    arxiv_max_concurrent_downloads: int = 5  # Maximum concurrent PDF downloads
    arxiv_max_concurrent_parsing: int = 3  # Maximum concurrent PDF parsing operations
    arxiv_namespaces: Dict[str, str] = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom"
    }

    # PDF Processing Configuration
    pdf_cache_dir: str = "./data/pdf_cache"
    pdf_max_pages: int = 50
    pdf_max_file_size_mb: int = 20
    pdf_do_ocr: bool = False
    pdf_do_table_structure: bool = True
    pdf_do_figure_extraction: bool = False
    pdf_timeout_seconds: int = 300
    pdf_cache_parsed_content: bool = True

    # Ingestion Workflow Settings
    ingestion_batch_size: int = 50
    ingestion_max_concurrent_jobs: int = 3
    ingestion_job_timeout_hours: int = 24
    ingestion_retry_max_attempts: int = 3
    ingestion_retry_delay_minutes: int = 5
    ingestion_cleanup_old_jobs_days: int = 30

    # Data Quality Settings
    quality_min_title_length: int = 10
    quality_min_abstract_length: int = 50
    quality_max_title_length: int = 500
    quality_max_abstract_length: int = 5000
    quality_check_duplicates: bool = True
    quality_duplicate_similarity_threshold: float = 0.95

    # Enterprise Features
    audit_log_enabled: bool = True
    audit_log_retention_days: int = 90
    rate_limit_ingestion_requests_per_hour: int = 10
    rate_limit_ingestion_burst: int = 5

    class Config:
        env_file = ".env"
        case_sensitive = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.strip("[]").split(",")]
        return v

    @field_validator("allowed_extensions", mode="before")
    @classmethod
    def parse_allowed_extensions(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.strip("[]").split(",")]
        return v


# Global settings instance
settings = Settings()