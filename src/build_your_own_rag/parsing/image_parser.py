"""Image parser using Docling (with EasyOCR) and raw EasyOCR fallback."""
from __future__ import annotations

import importlib.util
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


class ImageParseError(RuntimeError):
    """Raised when Image parsing fails."""


def parse_image(source: SourceDocument, strategy: ExtractionStrategy | None = None) -> ParsedDocument:
    # Images inherently require OCR
    strategy = strategy or ExtractionStrategy.OCR_ONLY
    parser_name = "docling"
    processing_started_at = utc_now_iso()
    docling_text: str | None = None
    docling_error: str | None = None
    status = "success"

    try:
        logger.info("Attempting Docling Image parse", extra={"extra_info": {"source_id": source.source_id}})
        docling_text = _parse_with_docling(source)
        logger.info("Docling Image parse successful", extra={"extra_info": {"source_id": source.source_id}})
    except Exception as exc:
        docling_error = str(exc)
        parser_name = "easyocr_fallback"
        status = "fallback"
        logger.warning(
            "Docling Image parse failed, falling back to raw easyocr",
            exc_info=exc,
            extra={"extra_info": {"source_id": source.source_id, "error": docling_error}}
        )

    image_metadata: dict[str, Any] = {}
    pages: list[ParsedPage] = []
    
    if status == "fallback" or docling_text is None:
        try:
            logger.info("Extracting Image text with EasyOCR fallback", extra={"extra_info": {"source_id": source.source_id}})
            pages, image_metadata = _extract_with_easyocr(source)
        except Exception as exc:
            logger.error(
                "Failed to extract Image text with EasyOCR",
                exc_info=exc,
                extra={"extra_info": {"source_id": source.source_id, "path": str(source.path)}}
            )
            raise ImageParseError(f"Failed to extract Image text from {source.path}: {exc}") from exc

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
            "ocr_used": True,
            "processing_status": status,
            "started_at": processing_started_at,
            "finished_at": processing_finished_at,
            "docling_error": docling_error,
        },
        format_specific={
            "image": image_metadata,
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
        ocr_used=True,
        status=status,
    )


def _parse_with_docling(source: SourceDocument) -> str:
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.document_converter import DocumentConverter, ImageFormatOption
        from docling.datamodel.pipeline_options import EasyOcrOptions, ImagePipelineOptions
    except Exception as exc:
        raise RuntimeError("Docling is not installed.") from exc
    
    if importlib.util.find_spec("easyocr") is None:
        raise RuntimeError("EasyOCR is required for image extraction.")

    pipeline_options = ImagePipelineOptions()
    pipeline_options.do_ocr = True
    try:
        pipeline_options.ocr_options = EasyOcrOptions(lang=["en"])
    except TypeError:
        pipeline_options.ocr_options = EasyOcrOptions()
        if hasattr(pipeline_options.ocr_options, "lang"):
            pipeline_options.ocr_options.lang = ["en"]

    converter = DocumentConverter(
        allowed_formats=[InputFormat.IMAGE],
        format_options={
            InputFormat.IMAGE: ImageFormatOption(pipeline_options=pipeline_options),
        }
    )
    result = converter.convert(str(source.path))
    document = result.document

    if hasattr(document, "export_to_markdown"):
        return document.export_to_markdown()
    if hasattr(document, "export_to_text"):
        return document.export_to_text()
    return str(document)


def _extract_with_easyocr(source: SourceDocument) -> tuple[list[ParsedPage], dict[str, Any]]:
    if importlib.util.find_spec("easyocr") is None:
        raise RuntimeError("easyocr is not installed. Run `pip install easyocr`.")
    
    import easyocr
    reader = easyocr.Reader(['en'])
    result = reader.readtext(str(source.path), detail=0)
    
    text = "\n".join(result)
    
    pages = [
        ParsedPage(
            page_number=1,
            text=text,
            metadata={"page_number": 1},
        )
    ]
    
    image_metadata = {
        "text_blocks_found": len(result),
    }
    
    return pages, image_metadata


def register() -> None:
    from build_your_own_rag.parsing.parser_registry import register_parser
    register_parser(".png", parse_image)
    register_parser(".jpg", parse_image)
    register_parser(".jpeg", parse_image)
