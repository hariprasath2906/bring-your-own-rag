import pytest

from build_your_own_rag.models import SourceDocument, ExtractionStrategy
from build_your_own_rag.parsing.text_parser import parse_text

@pytest.fixture
def sample_text_file(tmp_path):
    content = "This is line 1.\nThis is line 2.\nAnd line 3."
    file_path = tmp_path / "test.txt"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def test_parse_text(sample_text_file):
    source = SourceDocument(
        source_id="test_id_txt",
        source_type="local_txt",
        path=sample_text_file,
        filename="test.txt",
        extension="txt",
        size_bytes=sample_text_file.stat().st_size,
        mime_type="text/plain",
    )
    
    parsed = parse_text(source)
    
    assert parsed.parser_name == "text_native"
    assert parsed.source == source
    assert parsed.strategy is None
    
    assert "This is line 1." in parsed.text
    assert "This is line 2." in parsed.text
    
    txt_meta = parsed.metadata.format_specific["text"]
    assert txt_meta["line_count"] == 3
    assert txt_meta["char_count"] == 43
