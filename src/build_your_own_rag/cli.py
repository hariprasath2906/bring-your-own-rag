from __future__ import annotations

import argparse
import sys
from typing import Any

from build_your_own_rag.db.migrate import run_migrations
from build_your_own_rag.models import ExtractionStrategy, RetrievalMode
from build_your_own_rag.pipeline import chunk_source, embed_source_chunks, ingest_source, inspect_source, parse_source, ask_question
from build_your_own_rag.retrieval.hybrid import keyword_only, retrieve
from build_your_own_rag.storage.postgres import PostgresStore
from build_your_own_rag.utils.json import dumps, to_jsonable
from build_your_own_rag.utils.logger import get_logger

logger = get_logger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = args.func(args)
    except Exception as exc:
        logger.error("Command execution failed", exc_info=exc, extra={"extra_info": {"command": sys.argv}})
        return 1

    if result is not None:
        print(dumps(result))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local RAG MVP CLI")
    subparsers = parser.add_subparsers(required=True)

    inspect_parser = subparsers.add_parser("inspect-source", help="Inspect a local absolute PDF path")
    inspect_parser.add_argument("--path", required=True)
    inspect_parser.set_defaults(func=_inspect_source)

    parse_parser = subparsers.add_parser("parse", help="Parse a PDF")
    parse_parser.add_argument("--path", required=True)
    parse_parser.add_argument("--strategy", default="FAST", choices=[item.value for item in ExtractionStrategy])
    parse_parser.add_argument("--show-metadata", action="store_true")
    parse_parser.set_defaults(func=_parse)

    chunk_parser = subparsers.add_parser("chunk", help="Parse and chunk a PDF")
    chunk_parser.add_argument("--path", required=True)
    chunk_parser.add_argument("--strategy", default="FAST", choices=[item.value for item in ExtractionStrategy])
    chunk_parser.set_defaults(func=_chunk)

    embed_parser = subparsers.add_parser("embed", help="Embed PDF chunks")
    embed_parser.add_argument("--path", required=True)
    embed_parser.add_argument("--strategy", default="FAST", choices=[item.value for item in ExtractionStrategy])
    embed_parser.add_argument("--limit", type=int, default=3)
    embed_parser.set_defaults(func=_embed)

    migrate_parser = subparsers.add_parser("migrate", help="Run database migrations")
    migrate_parser.set_defaults(func=_migrate)

    ingest_parser = subparsers.add_parser("ingest", help="Ingest a PDF into PostgreSQL")
    ingest_parser.add_argument("--path", required=True)
    ingest_parser.add_argument("--strategy", default="FAST", choices=[item.value for item in ExtractionStrategy])
    ingest_parser.set_defaults(func=_ingest)

    retrieve_parser = subparsers.add_parser("retrieve", help="Retrieve chunks")
    retrieve_parser.add_argument("--query", required=True)
    retrieve_parser.add_argument("--top-k", type=int, default=5)
    retrieve_parser.add_argument("--mode", default="hybrid", choices=[item.value for item in RetrievalMode])
    retrieve_parser.add_argument("--source-type", default=None, help="Filter by source_type")
    retrieve_parser.add_argument("--source-id", default=None, help="Filter by source_id")
    retrieve_parser.set_defaults(func=_retrieve)

    keyword_parser = subparsers.add_parser("search-keyword", help="Run keyword-only search")
    keyword_parser.add_argument("--query", required=True)
    keyword_parser.add_argument("--top-k", type=int, default=5)
    keyword_parser.add_argument("--source-type", default=None, help="Filter by source_type")
    keyword_parser.add_argument("--source-id", default=None, help="Filter by source_id")
    keyword_parser.set_defaults(func=_search_keyword)

    ask_parser = subparsers.add_parser("ask", help="Ask a question and get an LLM-generated answer")
    ask_parser.add_argument("--query", required=True)
    ask_parser.add_argument("--top-k", type=int, default=5)
    ask_parser.add_argument("--mode", default="hybrid", choices=[item.value for item in RetrievalMode])
    ask_parser.add_argument("--model", default=None, help="Override the Ollama model")
    ask_parser.add_argument("--show-context", action="store_true", help="Also print the retrieved chunks")
    ask_parser.set_defaults(func=_ask)

    smoke_parser = subparsers.add_parser("smoke-test", help="Run local MVP smoke test")
    smoke_parser.add_argument("--path", required=True)
    smoke_parser.add_argument("--query", required=True)
    smoke_parser.add_argument("--strategy", default="FAST", choices=[item.value for item in ExtractionStrategy])
    smoke_parser.add_argument("--top-k", type=int, default=5)
    smoke_parser.set_defaults(func=_smoke_test)

    return parser


def _strategy(value: str) -> ExtractionStrategy:
    return ExtractionStrategy(value)


def _inspect_source(args: argparse.Namespace) -> Any:
    return inspect_source(args.path)


def _parse(args: argparse.Namespace) -> dict[str, Any]:
    parsed = parse_source(args.path, _strategy(args.strategy))
    response: dict[str, Any] = {
        "source": parsed.source,
        "parser_name": parsed.parser_name,
        "strategy": parsed.strategy,
        "ocr_used": parsed.ocr_used,
        "status": parsed.status,
        "page_count": len(parsed.pages),
        "character_count": len(parsed.text),
        "text_preview": parsed.text[:1000],
    }
    if args.show_metadata:
        response["metadata"] = parsed.metadata.as_dict()
    return response


def _chunk(args: argparse.Namespace) -> dict[str, Any]:
    chunks = chunk_source(args.path, _strategy(args.strategy))
    return {
        "chunk_count": len(chunks),
        "chunks": [
            {
                "chunk_index": chunk.chunk_index,
                "length_chars": len(chunk.content),
                "page_number": chunk.metadata.get("element", {}).get("page_number"),
                "preview": chunk.content[:300],
            }
            for chunk in chunks
        ],
    }


def _embed(args: argparse.Namespace) -> dict[str, Any]:
    chunks = embed_source_chunks(args.path, _strategy(args.strategy), limit=args.limit)
    return {
        "embedded_chunk_count": len(chunks),
        "chunks": [
            {
                "chunk_index": chunk.chunk_index,
                "embedding_dimensions": len(chunk.embedding or []),
                "embedding_preview": (chunk.embedding or [])[:5],
                "content_preview": chunk.content[:200],
            }
            for chunk in chunks
        ],
    }


def _migrate(args: argparse.Namespace) -> dict[str, Any]:
    run_migrations()
    return {"status": "migrations_completed"}


def _ingest(args: argparse.Namespace) -> Any:
    return ingest_source(args.path, _strategy(args.strategy))


def _retrieve(args: argparse.Namespace) -> Any:
    results = retrieve(
        args.query,
        args.top_k,
        RetrievalMode(args.mode),
        source_type=args.source_type,
        source_id=args.source_id,
    )
    return _format_results(results)


def _search_keyword(args: argparse.Namespace) -> Any:
    results = keyword_only(
        args.query,
        args.top_k,
        source_type=args.source_type,
        source_id=args.source_id,
    )
    return _format_results(results)


def _ask(args: argparse.Namespace) -> dict[str, Any]:
    gen_result = ask_question(
        query=args.query,
        top_k=args.top_k,
        mode=RetrievalMode(args.mode),
        model=args.model,
    )
    
    response = {
        "answer": gen_result.answer,
        "model": gen_result.model,
        "duration_ms": gen_result.duration_ms,
        "retrieval_mode": gen_result.retrieval_mode,
        "context_chunk_count": len(gen_result.context_chunks),
    }
    
    if args.show_context:
        response["context"] = _format_results(gen_result.context_chunks)
        
    return to_jsonable(response)


def _smoke_test(args: argparse.Namespace) -> dict[str, Any]:
    run_migrations()
    ingestion = ingest_source(args.path, _strategy(args.strategy))
    results = retrieve(args.query, args.top_k, RetrievalMode.HYBRID)
    store = PostgresStore()
    return {
        "migration": "ok",
        "database_health": store.health_check(),
        "ingestion": ingestion,
        "chunk_count": store.count_chunks(),
        "versions": store.list_versions(),
        "retrieval_count": len(results),
        "retrieval_results": _format_results(results),
    }


def _format_results(results) -> list[dict[str, Any]]:
    formatted = []
    for index, result in enumerate(results, start=1):
        formatted.append(
            {
                "rank": index,
                "chunk_id": result.chunk_id,
                "vector_score": result.vector_score,
                "keyword_score": result.keyword_score,
                "rrf_score": result.rrf_score,
                "rank_details": result.rank_details,
                "metadata": result.metadata,
                "content_preview": result.content[:700],
            }
        )
    return to_jsonable(formatted)


if __name__ == "__main__":
    raise SystemExit(main())
