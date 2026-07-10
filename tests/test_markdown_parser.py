import pytest
from pathlib import Path

from build_your_own_rag.models import SourceDocument, ExtractionStrategy
from build_your_own_rag.parsing.markdown_parser import parse_markdown

@pytest.fixture
def sample_markdown_file(tmp_path):
    content = """---
title: Test Document
author: Test Author
---

# Introduction
This is a test markdown file.

## Diagram
```mermaid
graph TD;
    A-->B;
```

## Image
![Test Image](http://example.com/image.png)
Bare image:
![](bare.png)
"""
    file_path = tmp_path / "test.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def test_parse_markdown(sample_markdown_file):
    source = SourceDocument(
        source_id="test_id",
        source_type="local_md",
        path=sample_markdown_file,
        filename="test.md",
        extension="md",
        size_bytes=sample_markdown_file.stat().st_size,
        mime_type="text/markdown",
    )
    
    parsed = parse_markdown(source)
    
    assert parsed.parser_name == "markdown_native"
    assert parsed.source == source
    assert parsed.strategy is None
    
    # Check that the text contains the semantic image replacements
    assert "[Image: Test Image]" in parsed.text
    assert "[Image: bare.png]" in parsed.text
    
    # Ensure the original mermaid block is preserved
    assert "```mermaid" in parsed.text
    assert "graph TD;" in parsed.text
    
    # Check metadata
    md_meta = parsed.metadata.format_specific["markdown"]
    assert md_meta["has_frontmatter"] is True
    assert md_meta["image_count"] == 2
    assert md_meta["diagram_count"] == 1
    assert md_meta["line_count"] > 10
