"""CSV parser with row-wise header context extraction."""
from __future__ import annotations

import csv

from build_your_own_rag.models import (
    DocumentMetadata,
    ExtractionStrategy,
    ParsedDocument,
    SourceDocument,
    utc_now_iso,
)
from build_your_own_rag.utils.logger import get_logger

logger = get_logger(__name__)


class CsvParseError(RuntimeError):
    """Raised when CSV parsing fails."""


def parse_csv(
    source: SourceDocument, strategy: ExtractionStrategy | None = None
) -> ParsedDocument:
    """Parse a CSV document, prepending headers to each row."""
    # Use FAST as default if no strategy is provided
    strategy = strategy or ExtractionStrategy.FAST
    parser_name = "csv_native"
    processing_started_at = utc_now_iso()
    status = "success"

    row_blocks = []
    row_count = 0
    column_count = 0
    
    try:
        with open(source.path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            try:
                headers = next(reader)
                column_count = len(headers)
            except StopIteration:
                headers = []

            for row in reader:
                row_count += 1
                if not any(row):
                    continue  # Skip completely empty rows
                
                # Combine header and row data
                cell_texts = []
                for i, cell in enumerate(row):
                    cell = cell.strip()
                    if not cell:
                        continue
                        
                    header = headers[i].strip() if i < len(headers) else f"Column_{i+1}"
                    if not header:
                        header = f"Column_{i+1}"
                        
                    cell_texts.append(f"{header}: {cell}")
                
                if cell_texts:
                    # Join cells of the row into a single block
                    row_blocks.append(" | ".join(cell_texts))
    except Exception as exc:
        status = "error"
        logger.error(
            "Failed to parse CSV",
            exc_info=exc,
            extra={"extra_info": {"source_id": source.source_id, "path": str(source.path)}}
        )
        raise CsvParseError(f"Failed to parse CSV {source.path}: {exc}") from exc

    text = "\n\n".join(row_blocks)
    processing_finished_at = utc_now_iso()

    format_metadata = {
        "csv": {
            "row_count": row_count,
            "column_count": column_count,
        }
    }

    metadata = DocumentMetadata(
        core={
            "filename": source.filename,
            "extension": source.extension,
            "source_path": str(source.path),
            "size_bytes": source.size_bytes,
            "mime_type": source.mime_type,
            "source_id": source.source_id,
            "source_type": source.source_type,
        },
        processing={
            "parser_name": parser_name,
            "requested_parser": "csv_native",
            "strategy": strategy.value,
            "ocr_used": False,
            "processing_status": status,
            "started_at": processing_started_at,
            "finished_at": processing_finished_at,
            "docling_error": None,
        },
        format_specific=format_metadata,
    )

    return ParsedDocument(
        source=source,
        text=text,
        pages=[],
        metadata=metadata,
        parser_name=parser_name,
        strategy=strategy,
        ocr_used=False,
        status=status,
    )

def register() -> None:
    """Register the CSV parser."""
    from build_your_own_rag.parsing.parser_registry import register_parser
    register_parser(".csv", parse_csv)
