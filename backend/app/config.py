import json
from functools import lru_cache
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application runtime configuration and environment variables."""

    # API Keys & LLM settings
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key")
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1", description="OpenAI API base URL")
    LLM_MODEL: str = Field(default="gpt-4o-mini", description="LLM model name for answering questions")
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", description="Embedding model name")

    # Vector store settings
    CHROMA_PERSIST_DIR: str = Field(default="./chroma_data", description="Local ChromaDB persistence directory")
    CHROMA_COLLECTION_NAME: str = Field(default="document_qa_collection", description="ChromaDB collection name")

    # Text processing and chunking
    CHUNK_SIZE: int = Field(default=600, ge=100, le=4000, description="Target chunk size in characters")
    CHUNK_OVERLAP: int = Field(default=120, ge=0, le=1000, description="Chunk overlap in characters")

    # Rate limiting & quotas
    RATE_LIMIT_PER_MINUTE: int = Field(default=20, ge=1, description="Max requests per minute per user/session")
    MAX_UPLOAD_SIZE_MB: int = Field(default=25, ge=1, le=100, description="Max allowed PDF upload size in megabytes")

    # Retrieval defaults
    DEFAULT_TOP_K: int = Field(default=4, ge=1, le=20, description="Default number of chunks retrieved")
    SIMILARITY_THRESHOLD: float = Field(default=0.15, ge=0.0, le=1.0, description="Minimum similarity score")

    # CORS settings
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "https://frontend-five-plum-90.vercel.app",
            "https://frontend-3snsyau3v-anugrah-ajiths-projects.vercel.app",
        ],
        description="Allowed CORS origins"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton provider for application settings."""
    return Settings()
