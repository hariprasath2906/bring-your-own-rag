from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "rag_db"
    postgres_user: str = "rag_user"
    postgres_password: str = "rag_password"
    embedding_model_name: str = "BAAI/bge-base-en-v1.5"
    chunk_target_tokens: int = 512
    chunk_overlap_ratio: float = 0.12
    # Average tokens-per-word for the target language and model.
    # English with bge-base-en-v1.5 averages ~1.3 tokens per word.
    # Used to convert token targets to word counts in the chunker.
    word_token_ratio: float = 1.3
    default_extraction_strategy: str = "FAST"
    rrf_k: int = 60
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "granite3.3:8b"
    ollama_temperature: float = 0.3

    @property
    def dsn(self) -> str:
        return (
            f"host={self.postgres_host} "
            f"port={self.postgres_port} "
            f"dbname={self.postgres_db} "
            f"user={self.postgres_user} "
            f"password={self.postgres_password}"
        )


def get_settings() -> Settings:
    """Build settings from environment variables at call time.

    Environment variables are read when this function is called, not at
    module import time, so tests and late configuration work correctly.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    return Settings(
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
        postgres_db=os.getenv("POSTGRES_DB", "rag_db"),
        postgres_user=os.getenv("POSTGRES_USER", "rag_user"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", "rag_password"),
        embedding_model_name=os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-base-en-v1.5"),
        chunk_target_tokens=int(os.getenv("CHUNK_TARGET_TOKENS", "512")),
        chunk_overlap_ratio=float(os.getenv("CHUNK_OVERLAP_RATIO", "0.12")),
        word_token_ratio=float(os.getenv("WORD_TOKEN_RATIO", "1.3")),
        default_extraction_strategy=os.getenv("DEFAULT_EXTRACTION_STRATEGY", "FAST"),
        rrf_k=int(os.getenv("RRF_K", "60")),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "granite3.3:8b"),
        ollama_temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.3")),
    )


