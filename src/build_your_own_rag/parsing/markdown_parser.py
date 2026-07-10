"""Native Markdown parser.

Reads Markdown files as raw text and prepares them for structural chunking.
Handles image references by extracting alt text for semantic context,
and preserves Mermaid/PlantUML blocks.
"""
from __future__ import annotations

import re

from build_your_own_rag.models import (
    DocumentMetadata,
    ExtractionStrategy,
    ParsedDocument,
    SourceDocument,
)

# Regex to match Markdown images: ![alt text](path "optional title")
IMAGE_REGEX = re.compile(r"!\[(.*?)\]\((.*?)\)")

# Regex to detect frontmatter blocks (--- at the start, followed by content, then ---)
FRONTMATTER_REGEX = re.compile(r"^---\n.*?\n---\n", re.DOTALL)

# Regex to detect diagram blocks
DIAGRAM_REGEX = re.compile(r"```(?:mermaid|plantuml).*?\n.*?```", re.DOTALL | re.IGNORECASE)


def parse_markdown(
    source: SourceDocument, strategy: ExtractionStrategy | None = None
) -> ParsedDocument:
    """Parse a Markdown document."""
    with open(source.path, "r", encoding="utf-8") as f:
        content = f.read()

    # Pre-process content to extract metadata and handle images
    line_count = content.count("\n") + 1
    has_frontmatter = bool(FRONTMATTER_REGEX.match(content))
    
    # Count images and diagrams
    images = IMAGE_REGEX.findall(content)
    image_count = len(images)
    diagram_count = len(DIAGRAM_REGEX.findall(content))

    # To make image references more semantic without breaking text flow,
    # replace ![alt text](image.png) with [Image: alt text] if alt text exists,
    # or just [Image: image.png] if no alt text.
    def replace_image(match: re.Match) -> str:
        alt_text = match.group(1).strip()
        path = match.group(2).strip().split()[0]  # ignore title if present
        if alt_text:
            return f"[Image: {alt_text}]"
        # Fallback to the filename if no alt text is provided
        filename = path.split("/")[-1]
        return f"[Image: {filename}]"

    processed_content = IMAGE_REGEX.sub(replace_image, content)

    # Format-specific metadata
    format_metadata = {
        "markdown": {
            "line_count": line_count,
            "has_frontmatter": has_frontmatter,
            "image_count": image_count,
            "diagram_count": diagram_count,
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
        text=processed_content,
        pages=[],
        metadata=metadata,
        parser_name="markdown_native",
        strategy=strategy,
    )

def register() -> None:
    """Register the markdown parser."""
    from build_your_own_rag.parsing.parser_registry import register_parser
    register_parser(".md", parse_markdown)
