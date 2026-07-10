"""Parser registry — dispatches file parsing to format-specific handlers.

Each parser function has the signature:
    (source: SourceDocument, strategy: ExtractionStrategy) -> ParsedDocument

Parsers are registered by file extension (e.g., ".pdf", ".md") and looked up
at runtime by ``parse_document()``.
"""
from __future__ import annotations

from typing import Callable

from build_your_own_rag.models import ExtractionStrategy, ParsedDocument, SourceDocument
from build_your_own_rag.utils.logger import get_logger

logger = get_logger(__name__)

# Type alias for any function that can parse a SourceDocument.
ParserFunc = Callable[[SourceDocument, ExtractionStrategy], ParsedDocument]

# Extension → parser mapping.  Populated by ``register_parser()`` calls
# inside each format-specific module's registration code.
_REGISTRY: dict[str, ParserFunc] = {}


def register_parser(extension: str, parser: ParserFunc) -> None:
    """Register a parser function for a file extension.

    Args:
        extension: Lowercase extension including the dot, e.g. ``".pdf"``.
        parser: A callable with the standard parser signature.
    """
    ext = extension.lower()
    if ext in _REGISTRY:
        logger.warning(
            "Overwriting existing parser registration",
            extra={"extra_info": {"extension": ext}},
        )
    _REGISTRY[ext] = parser
    logger.debug("Parser registered", extra={"extra_info": {"extension": ext}})


def parse_document(
    source: SourceDocument, strategy: ExtractionStrategy
) -> ParsedDocument:
    """Dispatch parsing to the handler registered for *source*'s extension.

    Raises ``ValueError`` if no parser is registered for the extension.
    """
    ext = f".{source.extension}"
    parser = _REGISTRY.get(ext)
    if parser is None:
        supported = ", ".join(sorted(_REGISTRY.keys()))
        raise ValueError(
            f"No parser registered for '{ext}'. Registered extensions: {supported}"
        )
    logger.info(
        "Dispatching to parser",
        extra={"extra_info": {"extension": ext, "source_id": source.source_id}},
    )
    return parser(source, strategy)


def registered_extensions() -> list[str]:
    """Return a sorted list of currently registered extensions."""
    return sorted(_REGISTRY.keys())
