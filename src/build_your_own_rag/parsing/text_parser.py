"""Native Plain Text parser.

Reads `.txt` files natively without any external dependencies.
"""
from __future__ import annotations

from build_your_own_rag.models import (
    DocumentMetadata,
    ExtractionStrategy,
    ParsedDocument,
    SourceDocument,
)


def parse_text(
    source: SourceDocument, strategy: ExtractionStrategy | None = None
) -> ParsedDocument:
    """Parse a Plain Text document."""
    with open(source.path, "r", encoding="utf-8") as f:
        content = f.read()

    line_count = content.count("\n") + 1
    char_count = len(content)

    format_metadata = {
        "text": {
            "line_count": line_count,
            "char_count": char_count,
            "encoding": "utf-8",
        }
    }

    metadata = DocumentMetadata(
        core={
            "source_id": source.source_id,
            "source_type": source.source_type,
            "filename": source.filename,
            "page_numbers": [],
        },
        processing={},
        format_specific=format_metadata,
    )

    return ParsedDocument(
        source=source,
        text=content,
        pages=[],
        metadata=metadata,
        parser_name="text_native",
        strategy=strategy,
    )

def register() -> None:
    """Register the text parser."""
    from build_your_own_rag.parsing.parser_registry import register_parser
    register_parser(".txt", parse_text)
