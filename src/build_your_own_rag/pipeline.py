from __future__ import annotations

from build_your_own_rag.chunking import build_chunks
from build_your_own_rag.embeddings import embed_texts
from build_your_own_rag.models import ExtractionStrategy, IngestionRun, ParsedDocument, SourceDocument, GenerationResult, RetrievalMode
from build_your_own_rag.parsing import parse_document
from build_your_own_rag.source import inspect_local_file
from build_your_own_rag.storage.postgres import PostgresStore
from build_your_own_rag.retrieval.hybrid import retrieve
from build_your_own_rag.generation.ollama import generate
from build_your_own_rag.utils.logger import get_logger

logger = get_logger(__name__)


def inspect_source(path: str) -> SourceDocument:
    logger.info("Inspecting source document", extra={"extra_info": {"path": path}})
    return inspect_local_file(path)


def parse_source(path: str, strategy: ExtractionStrategy) -> ParsedDocument:
    source = inspect_source(path)
    logger.info("Parsing source document", extra={"extra_info": {"source_id": source.source_id, "strategy": strategy.value}})
    return parse_document(source, strategy)


def chunk_source(path: str, strategy: ExtractionStrategy):
    parsed = parse_source(path, strategy)
    logger.info("Chunking parsed document", extra={"extra_info": {"source_id": parsed.source.source_id}})
    chunks = build_chunks(parsed)
    logger.info("Chunking complete", extra={"extra_info": {"source_id": parsed.source.source_id, "chunk_count": len(chunks)}})
    return chunks


def embed_source_chunks(path: str, strategy: ExtractionStrategy, limit: int | None = None):
    chunks = chunk_source(path, strategy)
    selected = chunks[:limit] if limit else chunks
    logger.info("Embedding chunks", extra={"extra_info": {"chunk_count": len(selected)}})
    vectors = embed_texts([chunk.content for chunk in selected])
    for chunk, vector in zip(selected, vectors, strict=True):
        chunk.embedding = vector
    return selected


def ingest_source(path: str, strategy: ExtractionStrategy) -> IngestionRun:
    logger.info("Starting ingestion pipeline", extra={"extra_info": {"path": path, "strategy": strategy.value}})
    parsed = parse_source(path, strategy)
    
    logger.info("Chunking document", extra={"extra_info": {"source_id": parsed.source.source_id}})
    chunks = build_chunks(parsed)
    
    logger.info("Embedding chunks", extra={"extra_info": {"source_id": parsed.source.source_id, "chunk_count": len(chunks)}})
    vectors = embed_texts([chunk.content for chunk in chunks])

    for chunk, vector in zip(chunks, vectors, strict=True):
        chunk.embedding = vector

    logger.info("Storing chunks to database", extra={"extra_info": {"source_id": parsed.source.source_id}})
    store = PostgresStore()
    run = store.save_new_version(parsed.source, parsed.metadata.as_dict(), chunks)
    
    if run.status == "active":
        logger.info("Ingestion completed successfully", extra={"extra_info": {"source_id": parsed.source.source_id, "version_number": run.version_number}})
    else:
        logger.error("Ingestion failed", extra={"extra_info": {"source_id": parsed.source.source_id, "error": run.error}})
        
    return run

def ask_question(query: str, top_k: int, mode: RetrievalMode, model: str | None = None) -> GenerationResult:
    logger.info("Starting ask pipeline", extra={"extra_info": {"query": query, "mode": mode.value, "model": model}})
    results = retrieve(query, top_k, mode)
    
    logger.info("Retrieved chunks for generation", extra={"extra_info": {"chunk_count": len(results)}})
    gen_result = generate(query, results, override_model=model)
    gen_result.retrieval_mode = mode.value
    
    return gen_result
