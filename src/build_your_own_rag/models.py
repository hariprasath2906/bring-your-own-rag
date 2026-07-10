from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class ExtractionStrategy(str, Enum):
    FAST = "FAST"
    HI_RES = "HI_RES"
    OCR_ONLY = "OCR_ONLY"

    @property
    def uses_ocr(self) -> bool:
        return self in {ExtractionStrategy.HI_RES, ExtractionStrategy.OCR_ONLY}


class RetrievalMode(str, Enum):
    VECTOR = "vector"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


@dataclass(frozen=True)
class SourceDocument:
    source_id: str
    source_type: str
    path: Path
    filename: str
    extension: str
    size_bytes: int
    mime_type: str


@dataclass
class DocumentMetadata:
    core: dict[str, Any]
    processing: dict[str, Any]
    format_specific: dict[str, Any]
    elements: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "core": self.core,
            "processing": self.processing,
            "format_specific": self.format_specific,
            "elements": self.elements,
        }


@dataclass
class ParsedPage:
    page_number: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    source: SourceDocument
    text: str
    pages: list[ParsedPage]
    metadata: DocumentMetadata
    parser_name: str
    # strategy is None for formats where ExtractionStrategy doesn't apply
    # (e.g., Markdown, plain text, CSV).
    strategy: ExtractionStrategy | None = None
    ocr_used: bool = False
    status: str = "success"


@dataclass
class ChunkRecord:
    source_id: str
    source_type: str
    chunk_index: int
    content: str
    metadata: dict[str, Any]
    embedding: list[float] | None = None


@dataclass
class IngestionRun:
    source_id: str
    version_number: int
    status: str
    chunk_count: int
    error: str | None = None


@dataclass
class RetrievalResult:
    chunk_id: int
    content: str
    metadata: dict[str, Any]
    vector_score: float | None = None
    keyword_score: float | None = None
    rrf_score: float | None = None
    rank_details: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    answer: str
    model: str
    query: str
    context_chunks: list[RetrievalResult]
    retrieval_mode: str
    duration_ms: int | None = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

