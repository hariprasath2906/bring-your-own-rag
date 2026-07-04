from __future__ import annotations

from typing import Any

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


class PdfParseError(RuntimeError):
    """Raised when PDF parsing fails."""


def parse_pdf(source: SourceDocument, strategy: ExtractionStrategy) -> ParsedDocument:
    parser_name = "docling"
    processing_started_at = utc_now_iso()
    docling_text: str | None = None
    docling_error: str | None = None
    status = "success"

    try:
        logger.info("Attempting Docling parse", extra={"extra_info": {"source_id": source.source_id}})
        docling_text = _parse_with_docling(source, strategy)
        logger.info("Docling parse successful", extra={"extra_info": {"source_id": source.source_id}})
    except Exception as exc:  # pragma: no cover - depends on optional Docling runtime
        docling_error = str(exc)
        parser_name = "pypdf_fallback"
        status = "fallback"
        logger.warning(
            "Docling parse failed, falling back to pypdf", 
            exc_info=exc, 
            extra={"extra_info": {"source_id": source.source_id, "error": docling_error}}
        )

    try:
        logger.info("Extracting PDF metadata/pages with pypdf", extra={"extra_info": {"source_id": source.source_id}})
        pages, pdf_metadata = _extract_with_pypdf(source)
    except Exception as exc:
        logger.error(
            "Failed to extract PDF text with pypdf", 
            exc_info=exc,
            extra={"extra_info": {"source_id": source.source_id, "path": str(source.path)}}
        )
        raise PdfParseError(f"Failed to extract PDF text from {source.path}: {exc}") from exc

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
            "ocr_used": strategy.uses_ocr,
            "ocr_language": "en" if strategy.uses_ocr else None,
            "processing_status": status,
            "started_at": processing_started_at,
            "finished_at": processing_finished_at,
            "docling_error": docling_error,
        },
        format_specific={
            "pdf": pdf_metadata,
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
        ocr_used=strategy.uses_ocr,
        status=status,
    )


def _parse_with_docling(source: SourceDocument, strategy: ExtractionStrategy) -> str:
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import EasyOcrOptions, PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
    except Exception as exc:
        raise RuntimeError("Docling is not installed. Install requirements or use the Docker app image.") from exc

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = strategy.uses_ocr
    pipeline_options.do_table_structure = strategy != ExtractionStrategy.FAST

    try:
        pipeline_options.ocr_options = EasyOcrOptions(lang=["en"])
    except TypeError:
        pipeline_options.ocr_options = EasyOcrOptions()
        if hasattr(pipeline_options.ocr_options, "lang"):
            pipeline_options.ocr_options.lang = ["en"]

    if strategy == ExtractionStrategy.OCR_ONLY:
        for attr in ("force_full_page_ocr", "force_ocr", "ocr_only"):
            if hasattr(pipeline_options, attr):
                setattr(pipeline_options, attr, True)

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )
    result = converter.convert(str(source.path))
    document = result.document

    if hasattr(document, "export_to_markdown"):
        return document.export_to_markdown()
    if hasattr(document, "export_to_text"):
        return document.export_to_text()
    return str(document)


def _extract_with_pypdf(source: SourceDocument) -> tuple[list[ParsedPage], dict[str, Any]]:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise RuntimeError("pypdf is not installed. Install requirements or run the Docker app image.") from exc

    reader = PdfReader(str(source.path))
    raw_metadata = reader.metadata or {}
    pages: list[ParsedPage] = []

    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        pages.append(
            ParsedPage(
                page_number=index,
                text=page_text.strip(),
                metadata={
                    "page_number": index,
                },
            )
        )

    pdf_metadata = {
        "page_count": len(reader.pages),
        "is_encrypted": bool(reader.is_encrypted),
        "pdf_version": getattr(reader, "pdf_header", None),
        "document_info": {str(k): str(v) for k, v in raw_metadata.items()},
    }
    return pages, pdf_metadata
