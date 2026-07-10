"""HTML parser using Docling with BeautifulSoup/html2text fallback."""
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


class HtmlParseError(RuntimeError):
    """Raised when HTML parsing fails."""


def parse_html(source: SourceDocument, strategy: ExtractionStrategy | None = None) -> ParsedDocument:
    # Use FAST as default if no strategy is provided
    strategy = strategy or ExtractionStrategy.FAST
    parser_name = "docling"
    processing_started_at = utc_now_iso()
    docling_text: str | None = None
    docling_error: str | None = None
    status = "success"

    try:
        logger.info("Attempting Docling HTML parse", extra={"extra_info": {"source_id": source.source_id}})
        docling_text = _parse_with_docling(source)
        logger.info("Docling HTML parse successful", extra={"extra_info": {"source_id": source.source_id}})
    except Exception as exc:
        docling_error = str(exc)
        parser_name = "beautifulsoup_fallback"
        status = "fallback"
        logger.warning(
            "Docling HTML parse failed, falling back to beautifulsoup4 + html2text",
            exc_info=exc,
            extra={"extra_info": {"source_id": source.source_id, "error": docling_error}}
        )

    html_metadata: dict[str, Any] = {}
    pages: list[ParsedPage] = []
    
    if status == "fallback" or docling_text is None:
        try:
            logger.info("Extracting HTML text with bs4 fallback", extra={"extra_info": {"source_id": source.source_id}})
            pages, html_metadata = _extract_with_bs4(source)
        except Exception as exc:
            logger.error(
                "Failed to extract HTML text with bs4 fallback",
                exc_info=exc,
                extra={"extra_info": {"source_id": source.source_id, "path": str(source.path)}}
            )
            raise HtmlParseError(f"Failed to extract HTML text from {source.path}: {exc}") from exc

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
            "html": html_metadata,
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

    converter = DocumentConverter(allowed_formats=[InputFormat.HTML])
    result = converter.convert(str(source.path))
    document = result.document

    if hasattr(document, "export_to_markdown"):
        return document.export_to_markdown()
    if hasattr(document, "export_to_text"):
        return document.export_to_text()
    return str(document)


def _extract_with_bs4(source: SourceDocument) -> tuple[list[ParsedPage], dict[str, Any]]:
    if importlib.util.find_spec("bs4") is None or importlib.util.find_spec("html2text") is None:
        raise RuntimeError(
            "beautifulsoup4 or html2text is not installed. "
            "Install requirements.txt or run `python -m pip install beautifulsoup4 html2text`."
        )
    
    from bs4 import BeautifulSoup
    import html2text

    with open(source.path, "r", encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")
    
    # Extract metadata before stripping tags
    title_tag = soup.title
    title = title_tag.string.strip() if title_tag and title_tag.string else None
    
    tables = soup.find_all("table")
    links = soup.find_all("a")

    # Strip script and style elements
    for script_or_style in soup(["script", "style", "nav", "footer", "header"]):
        script_or_style.extract()

    # Convert to Markdown using html2text
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0  # No wrapping
    
    markdown_text = h.handle(str(soup))
    
    pages = [
        ParsedPage(
            page_number=1,
            text=markdown_text.strip(),
            metadata={"page_number": 1},
        )
    ]
    
    html_metadata = {
        "title": title,
        "table_count": len(tables),
        "link_count": len(links),
    }
    
    return pages, html_metadata


def register() -> None:
    from build_your_own_rag.parsing.parser_registry import register_parser
    register_parser(".html", parse_html)
    register_parser(".htm", parse_html)
