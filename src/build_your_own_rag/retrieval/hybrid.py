from __future__ import annotations

from build_your_own_rag.config import get_settings
from build_your_own_rag.embeddings import embed_query
from build_your_own_rag.models import RetrievalMode, RetrievalResult
from build_your_own_rag.storage.postgres import PostgresStore


def retrieve(
    query: str,
    top_k: int,
    mode: RetrievalMode,
    source_type: str | None = None,
    source_id: str | None = None,
) -> list[RetrievalResult]:
    store = PostgresStore()

    if mode == RetrievalMode.VECTOR:
        query_vector = embed_query(query)
        return _from_vector_rows(
            store.vector_search(query_vector, top_k, source_type=source_type, source_id=source_id)
        )

    if mode == RetrievalMode.KEYWORD:
        return _from_keyword_rows(
            store.keyword_search(query, top_k, source_type=source_type, source_id=source_id)
        )

    # Hybrid: fetch expanded candidate sets from both sources, then merge via RRF.
    expanded = top_k * 2
    query_vector = embed_query(query)
    vector_rows = store.vector_search(query_vector, expanded, source_type=source_type, source_id=source_id)
    keyword_rows = store.keyword_search(query, expanded, source_type=source_type, source_id=source_id)
    return _rrf_merge(vector_rows, keyword_rows)[:top_k]


def keyword_only(
    query: str,
    top_k: int,
    source_type: str | None = None,
    source_id: str | None = None,
) -> list[RetrievalResult]:
    return _from_keyword_rows(
        PostgresStore().keyword_search(query, top_k, source_type=source_type, source_id=source_id)
    )


def _from_vector_rows(rows: list[dict]) -> list[RetrievalResult]:
    return [
        RetrievalResult(
            chunk_id=int(row["chunk_id"]),
            content=row["content"],
            metadata=row["metadata"],
            vector_score=float(row["vector_score"]),
            rank_details={"vector_rank": index},
        )
        for index, row in enumerate(rows, start=1)
    ]


def _from_keyword_rows(rows: list[dict]) -> list[RetrievalResult]:
    return [
        RetrievalResult(
            chunk_id=int(row["chunk_id"]),
            content=row["content"],
            metadata=row["metadata"],
            keyword_score=float(row["keyword_score"]),
            rank_details={"keyword_rank": index},
        )
        for index, row in enumerate(rows, start=1)
    ]


def _rrf_merge(vector_rows: list[dict], keyword_rows: list[dict]) -> list[RetrievalResult]:
    settings = get_settings()
    merged: dict[int, RetrievalResult] = {}

    for rank, row in enumerate(vector_rows, start=1):
        chunk_id = int(row["chunk_id"])
        merged[chunk_id] = RetrievalResult(
            chunk_id=chunk_id,
            content=row["content"],
            metadata=row["metadata"],
            vector_score=float(row["vector_score"]),
            rrf_score=1.0 / (settings.rrf_k + rank),
            rank_details={"vector_rank": rank},
        )

    for rank, row in enumerate(keyword_rows, start=1):
        chunk_id = int(row["chunk_id"])
        increment = 1.0 / (settings.rrf_k + rank)
        if chunk_id in merged:
            result = merged[chunk_id]
            result.keyword_score = float(row["keyword_score"])
            result.rrf_score = (result.rrf_score or 0.0) + increment
            result.rank_details["keyword_rank"] = rank
        else:
            merged[chunk_id] = RetrievalResult(
                chunk_id=chunk_id,
                content=row["content"],
                metadata=row["metadata"],
                keyword_score=float(row["keyword_score"]),
                rrf_score=increment,
                rank_details={"keyword_rank": rank},
            )

    return sorted(merged.values(), key=lambda item: item.rrf_score or 0.0, reverse=True)

