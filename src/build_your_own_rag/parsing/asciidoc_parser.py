"""AsciiDoc parser using Docling."""
from __future__ import annotations

from build_your_own_rag.models import (
    DocumentMetadata,
    ExtractionStrategy,
    ParsedDocument,
    ParsedPage,
    SourceDocument,
    utc_now_iso,
)
from build_your_own_rag.utils.logger import get_logger

logger = get_logger(__name__)


class AsciiDocParseError(RuntimeError):
    """Raised when AsciiDoc parsing fails."""


def parse_asciidoc(source: SourceDocument, strategy: ExtractionStrategy | None = None) -> ParsedDocument:
    strategy = strategy or ExtractionStrategy.FAST
    parser_name = "docling"
    processing_started_at = utc_now_iso()
    docling_text: str | None = None
    docling_error: str | None = None
    status = "success"

    try:
        logger.info("Attempting Docling AsciiDoc parse", extra={"extra_info": {"source_id": source.source_id}})
        docling_text = _parse_with_docling(source)
        logger.info("Docling AsciiDoc parse successful", extra={"extra_info": {"source_id": source.source_id}})
    except Exception as exc:
        docling_error = str(exc)
        parser_name = "text_fallback"
        status = "fallback"
        logger.warning(
            "Docling AsciiDoc parse failed, falling back to plain text",
            exc_info=exc,
            extra={"extra_info": {"source_id": source.source_id, "error": docling_error}}
        )

    adoc_metadata: dict[str, str] = {}
    pages: list[ParsedPage] = []
    
    if status == "fallback" or docling_text is None:
        try:
            logger.info("Extracting AsciiDoc text with plain text fallback", extra={"extra_info": {"source_id": source.source_id}})
            with open(source.path, "r", encoding="utf-8") as f:
                content = f.read()
            pages = [
                ParsedPage(
                    page_number=1,
                    text=content.strip(),
                    metadata={"page_number": 1},
                )
            ]
        except Exception as exc:
            logger.error(
                "Failed to extract AsciiDoc text with fallback",
                exc_info=exc,
                extra={"extra_info": {"source_id": source.source_id, "path": str(source.path)}}
            )
            raise AsciiDocParseError(f"Failed to extract AsciiDoc text from {source.path}: {exc}") from exc

    text = (docling_text or "\n\n".join(page.text for page in pages)).strip()
    processing_finished_at = utc_now_iso()

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
            "requested_parser": "docling",
            "strategy": strategy.value,
            "ocr_used": False,
            "processing_status": status,
            "started_at": processing_started_at,
            "finished_at": processing_finished_at,
            "docling_error": docling_error,
        },
        format_specific={
            "asciidoc": adoc_metadata,
        },
        elements=[
            {
                "page_number": page.page_number,
                "section_hierarchy": None,
                "coordinates": None,
                "style_name": None,
                "formatting": None,
                "language": "en",
            }
            for page in pages
        ],
    )

    return ParsedDocument(
        source=source,
        text=text,
        pages=pages,
        metadata=metadata,
        parser_name=parser_name,
        strategy=strategy,
        ocr_used=False,
        status=status,
    )


def _parse_with_docling(source: SourceDocument) -> str:
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.document_converter import DocumentConverter
    except Exception as exc:
        raise RuntimeError("Docling is not installed.") from exc

    converter = DocumentConverter(allowed_formats=[InputFormat.ASCIIDOC])
    result = converter.convert(str(source.path))
    document = result.document

    if hasattr(document, "export_to_markdown"):
        return document.export_to_markdown()
    if hasattr(document, "export_to_text"):
        return document.export_to_text()
    return str(document)


def register() -> None:
    from build_your_own_rag.parsing.parser_registry import register_parser
    register_parser(".adoc", parse_asciidoc)
    register_parser(".asciidoc", parse_asciidoc)
