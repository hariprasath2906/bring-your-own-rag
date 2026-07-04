from __future__ import annotations

import hashlib
import math
import os
from functools import lru_cache

from build_your_own_rag.config import get_settings


class EmbeddingError(RuntimeError):
    """Raised when embedding generation fails."""


@lru_cache(maxsize=1)
def _load_model():
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:
        raise EmbeddingError(
            "sentence-transformers is not installed. Install requirements or run the Docker app image."
        ) from exc

    settings = get_settings()
    try:
        return SentenceTransformer(settings.embedding_model_name)
    except Exception as exc:
        raise EmbeddingError(
            f"Failed to load embedding model {settings.embedding_model_name}. "
            "Check network/model cache or use the Docker app after dependencies are installed."
        ) from exc


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    if os.getenv("USE_HASH_EMBEDDINGS", "0") == "1":
        return [_hash_embedding(text) for text in texts]

    model = _load_model()
    vectors = model.encode(texts, batch_size=16, normalize_embeddings=True)
    result = [list(map(float, vector)) for vector in vectors]
    _validate_vectors(result)
    return result


def embed_query(query: str) -> list[float]:
    return embed_texts([query])[0]


def _validate_vectors(vectors: list[list[float]]) -> None:
    for vector in vectors:
        if len(vector) != 768:
            raise EmbeddingError(f"Expected 768-dimensional embedding, got {len(vector)}")


def _hash_embedding(text: str) -> list[float]:
    values: list[float] = []
    counter = 0
    while len(values) < 768:
        digest = hashlib.sha256(f"{counter}:{text}".encode("utf-8")).digest()
        for byte in digest:
            values.append((byte / 255.0) - 0.5)
            if len(values) == 768:
                break
        counter += 1
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]

