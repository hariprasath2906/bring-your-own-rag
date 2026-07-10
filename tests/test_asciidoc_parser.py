import pytest
from pathlib import Path

from build_your_own_rag.models import SourceDocument, ExtractionStrategy
from build_your_own_rag.parsing.asciidoc_parser import parse_asciidoc

@pytest.fixture
def sample_adoc_file(tmp_path):
    content = """= AsciiDoc Test Document
Author Name
:toc:

== Introduction
This is a test AsciiDoc file.

== Table
|===
| Header 1 | Header 2
| Value 1 | Value 2
|===
"""
    file_path = tmp_path / "test.adoc"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def test_parse_asciidoc_success(sample_adoc_file):
    source = SourceDocument(
        source_id="test_id_adoc",
        source_type="local_asciidoc",
        path=sample_adoc_file,
        filename="test.adoc",
        extension="adoc",
        size_bytes=sample_adoc_file.stat().st_size,
        mime_type="text/asciidoc",
    )
    
    parsed = parse_asciidoc(source, strategy=ExtractionStrategy.FAST)
    
    assert parsed.parser_name == "docling"
    assert parsed.source == source
    
    assert "This is a test AsciiDoc file." in parsed.text
    
    assert "asciidoc" in parsed.metadata.format_specific

def test_parse_asciidoc_fallback(monkeypatch, sample_adoc_file):
    source = SourceDocument(
        source_id="test_id_adoc_fallback",
        source_type="local_asciidoc",
        path=sample_adoc_file,
        filename="test.adoc",
        extension="adoc",
        size_bytes=sample_adoc_file.stat().st_size,
        mime_type="text/asciidoc",
    )
    
    def mock_parse_with_docling(*args, **kwargs):
        raise RuntimeError("Mock Docling failure")
    
    import build_your_own_rag.parsing.asciidoc_parser as adoc_module
    monkeypatch.setattr(adoc_module, "_parse_with_docling", mock_parse_with_docling)
    
    parsed = parse_asciidoc(source, strategy=ExtractionStrategy.FAST)
    
    assert parsed.parser_name == "text_fallback"
    assert parsed.status == "fallback"
    
    # Check that actual content was retained
    assert "This is a test AsciiDoc file." in parsed.text
