import pytest
from pathlib import Path

from build_your_own_rag.models import SourceDocument, ExtractionStrategy
from build_your_own_rag.parsing.html_parser import parse_html

@pytest.fixture
def sample_html_file(tmp_path):
    content = """<!DOCTYPE html>
<html>
<head>
    <title>Test HTML Document</title>
    <style>
        body { font-family: Arial; }
    </style>
</head>
<body>
    <header>Site Header</header>
    <nav>
        <a href="/">Home</a>
    </nav>
    <h1>Main Content</h1>
    <p>This is a test HTML file.</p>
    <table>
        <tr><th>Header</th></tr>
        <tr><td>Data</td></tr>
    </table>
    <script>
        console.log("Ignore this");
    </script>
    <footer>Site Footer</footer>
</body>
</html>
"""
    file_path = tmp_path / "test.html"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def test_parse_html_success(sample_html_file):
    source = SourceDocument(
        source_id="test_id_html",
        source_type="local_html",
        path=sample_html_file,
        filename="test.html",
        extension="html",
        size_bytes=sample_html_file.stat().st_size,
        mime_type="text/html",
    )
    
    parsed = parse_html(source, strategy=ExtractionStrategy.FAST)
    
    assert parsed.parser_name == "docling"
    assert parsed.source == source
    
    assert "Main Content" in parsed.text
    assert "This is a test HTML file." in parsed.text
    assert "Data" in parsed.text
    
    assert "html" in parsed.metadata.format_specific

def test_parse_html_fallback(monkeypatch, sample_html_file):
    source = SourceDocument(
        source_id="test_id_html_fallback",
        source_type="local_html",
        path=sample_html_file,
        filename="test.html",
        extension="html",
        size_bytes=sample_html_file.stat().st_size,
        mime_type="text/html",
    )
    
    def mock_parse_with_docling(*args, **kwargs):
        raise RuntimeError("Mock Docling failure")
    
    import build_your_own_rag.parsing.html_parser as html_module
    monkeypatch.setattr(html_module, "_parse_with_docling", mock_parse_with_docling)
    
    parsed = parse_html(source, strategy=ExtractionStrategy.FAST)
    
    assert parsed.parser_name == "beautifulsoup_fallback"
    assert parsed.status == "fallback"
    
    # Check that headers/scripts were stripped
    assert "Site Header" not in parsed.text
    assert "Site Footer" not in parsed.text
    assert "console.log" not in parsed.text
    
    # Check that actual content was retained
    assert "Main Content" in parsed.text
    assert "This is a test HTML file." in parsed.text
    assert "Data" in parsed.text
    
    html_meta = parsed.metadata.format_specific["html"]
    assert html_meta["title"] == "Test HTML Document"
    assert html_meta["table_count"] == 1
    assert html_meta["link_count"] == 1
