"""Parsing adapters.

This package provides a unified ``parse_document()`` entry point that
dispatches to format-specific parsers based on the source file's extension.

Parsers are registered via the ``parser_registry`` module.  Each format
module (e.g. ``docling_parser``) registers its handler(s) when this
package is first imported.
"""

from build_your_own_rag.parsing.parser_registry import (  # noqa: F401
    parse_document,
    register_parser,
    registered_extensions,
)

# ── Register built-in parsers ────────────────────────────────────────────
# Each import triggers the module-level ``register_parser()`` call inside
# each format module. New format modules should follow the same pattern
# and be imported here.
from build_your_own_rag.parsing.docling_parser import parse_pdf  # noqa: F401
from build_your_own_rag.parsing.markdown_parser import parse_markdown  # noqa: F401
from build_your_own_rag.parsing.text_parser import parse_text  # noqa: F401
from build_your_own_rag.parsing.docx_parser import parse_docx  # noqa: F401
from build_your_own_rag.parsing.html_parser import parse_html  # noqa: F401
from build_your_own_rag.parsing.pptx_parser import parse_pptx  # noqa: F401
from build_your_own_rag.parsing.csv_parser import parse_csv  # noqa: F401
from build_your_own_rag.parsing.xlsx_parser import parse_xlsx  # noqa: F401

register_parser(".pdf", parse_pdf)
register_parser(".md", parse_markdown)
register_parser(".txt", parse_text)
register_parser(".docx", parse_docx)
register_parser(".html", parse_html)
register_parser(".htm", parse_html)
register_parser(".pptx", parse_pptx)
register_parser(".csv", parse_csv)
register_parser(".xlsx", parse_xlsx)
