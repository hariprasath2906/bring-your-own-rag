from __future__ import annotations

import json
from typing import Any

from build_your_own_rag.config import get_settings
from build_your_own_rag.models import ChunkRecord, IngestionRun, SourceDocument
from build_your_own_rag.utils.json import to_jsonable


class StorageError(RuntimeError):
    """Raised when database storage fails."""


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.10f}" for value in vector) + "]"


_pool = None

def get_pool():
    global _pool
    if _pool is None:
        try:
            from psycopg_pool import ConnectionPool
            from psycopg.rows import dict_row
        except Exception as exc:
            raise StorageError("psycopg[pool] is not installed. Install requirements or run inside Docker.") from exc
        
        settings = get_settings()
        _pool = ConnectionPool(settings.dsn, min_size=1, max_size=10, kwargs={"row_factory": dict_row})
    return _pool


class PostgresStore:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _connect(self):
        return get_pool().connection()

    def health_check(self) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 AS ok").fetchone()
            return bool(row and row["ok"] == 1)

    def save_new_version(
        self,
        source: SourceDocument,
        document_metadata: dict[str, Any],
        chunks: list[ChunkRecord],
    ) -> IngestionRun:
        if not chunks:
            raise StorageError("No chunks were produced; refusing to create an active empty version.")
        for chunk in chunks:
            if chunk.embedding is None:
                raise StorageError(f"Chunk {chunk.chunk_index} has no embedding.")

        with self._connect() as conn:
            with conn.transaction():
                document_id = self._upsert_document(conn, source)
                version_number = self._next_version_number(conn, document_id)
                version_id = self._create_version(conn, document_id, source, version_number, document_metadata)

                for chunk in chunks:
                    conn.execute(
                        """
                        INSERT INTO chunks (
                            document_id, version_id, source_id, source_type,
                            chunk_index, content, embedding, metadata
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s::vector, %s::jsonb)
                        """,
                        (
                            document_id,
                            version_id,
                            chunk.source_id,
                            chunk.source_type,
                            chunk.chunk_index,
                            chunk.content,
                            vector_literal(chunk.embedding or []),
                            json.dumps(to_jsonable(chunk.metadata)),
                        ),
                    )

                conn.execute(
                    """
                    UPDATE document_versions
                    SET is_active = FALSE, status = 'retired'
                    WHERE document_id = %s AND is_active = TRUE
                    """,
                    (document_id,),
                )
                conn.execute(
                    """
                    UPDATE document_versions
                    SET is_active = TRUE, status = 'active', activated_at = now()
                    WHERE id = %s
                    """,
                    (version_id,),
                )

        return IngestionRun(
            source_id=source.source_id,
            version_number=version_number,
            status="active",
            chunk_count=len(chunks),
        )

    def vector_search(
        self,
        query_embedding: list[float],
        top_k: int,
        source_type: str | None = None,
        source_id: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    c.id AS chunk_id,
                    c.content,
                    c.metadata,
                    c.embedding <=> %s::vector AS distance,
                    1 - (c.embedding <=> %s::vector) AS vector_score
                FROM chunks c
                JOIN document_versions v ON v.id = c.version_id
                WHERE v.is_active = TRUE
                  AND (%s::text IS NULL OR c.source_type = %s)
                  AND (%s::text IS NULL OR c.source_id = %s)
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
                """,
                (
                    vector_literal(query_embedding),
                    vector_literal(query_embedding),
                    source_type,
                    source_type,
                    source_id,
                    source_id,
                    vector_literal(query_embedding),
                    top_k,
                ),
            ).fetchall()
            return list(rows)

    def keyword_search(
        self,
        query: str,
        top_k: int,
        source_type: str | None = None,
        source_id: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    c.id AS chunk_id,
                    c.content,
                    c.metadata,
                    ts_rank_cd(c.search_vector, plainto_tsquery('english', %s)) AS keyword_score
                FROM chunks c
                JOIN document_versions v ON v.id = c.version_id
                WHERE v.is_active = TRUE
                  AND c.search_vector @@ plainto_tsquery('english', %s)
                  AND (%s::text IS NULL OR c.source_type = %s)
                  AND (%s::text IS NULL OR c.source_id = %s)
                ORDER BY keyword_score DESC
                LIMIT %s
                """,
                (query, query, source_type, source_type, source_id, source_id, top_k),
            ).fetchall()
            return list(rows)

    def count_chunks(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT count(*) AS count FROM chunks").fetchone()
            return int(row["count"])

    def list_versions(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT source_id, version_number, is_active, status, created_at, activated_at
                FROM document_versions
                ORDER BY source_id, version_number
                """
            ).fetchall()
            return list(rows)

    def _upsert_document(self, conn, source: SourceDocument) -> int:
        row = conn.execute(
            """
            INSERT INTO documents (source_id, source_type, source_path, filename, mime_type)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (source_id)
            DO UPDATE SET
                source_type = EXCLUDED.source_type,
                source_path = EXCLUDED.source_path,
                filename = EXCLUDED.filename,
                mime_type = EXCLUDED.mime_type,
                updated_at = now()
            RETURNING id
            """,
            (source.source_id, source.source_type, str(source.path), source.filename, source.mime_type),
        ).fetchone()
        return int(row["id"])

    def _next_version_number(self, conn, document_id: int) -> int:
        row = conn.execute(
            "SELECT coalesce(max(version_number), 0) + 1 AS next_version FROM document_versions WHERE document_id = %s",
            (document_id,),
        ).fetchone()
        return int(row["next_version"])

    def _create_version(
        self,
        conn,
        document_id: int,
        source: SourceDocument,
        version_number: int,
        metadata: dict[str, Any],
    ) -> int:
        row = conn.execute(
            """
            INSERT INTO document_versions (document_id, source_id, version_number, status, is_active, metadata)
            VALUES (%s, %s, %s, 'processing', FALSE, %s::jsonb)
            RETURNING id
            """,
            (document_id, source.source_id, version_number, json.dumps(to_jsonable(metadata))),
        ).fetchone()
        return int(row["id"])

