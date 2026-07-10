import pytest
from pathlib import Path
from PIL import Image

from build_your_own_rag.models import SourceDocument, ExtractionStrategy
from build_your_own_rag.parsing.image_parser import parse_image

@pytest.fixture
def sample_image_file(tmp_path):
    file_path = tmp_path / "test.png"
    # Create a dummy image
    img = Image.new('RGB', (100, 30), color = (73, 109, 137))
    img.save(file_path)
    return file_path


def test_parse_image_success(monkeypatch, sample_image_file):
    source = SourceDocument(
        source_id="test_id_img",
        source_type="local_image",
        path=sample_image_file,
        filename="test.png",
        extension="png",
        size_bytes=sample_image_file.stat().st_size,
        mime_type="image/png",
    )
    
    # Mock Docling parse to avoid heavy OCR model downloads in CI
    def mock_parse_with_docling(*args, **kwargs):
        return "Mocked OCR Text from Docling"
    
    import build_your_own_rag.parsing.image_parser as img_module
    monkeypatch.setattr(img_module, "_parse_with_docling", mock_parse_with_docling)
    
    parsed = parse_image(source, strategy=ExtractionStrategy.OCR_ONLY)
    
    assert parsed.parser_name == "docling"
    assert parsed.source == source
    assert parsed.status == "success"
    assert parsed.text == "Mocked OCR Text from Docling"
    assert parsed.ocr_used is True
    
def test_parse_image_fallback(monkeypatch, sample_image_file):
    source = SourceDocument(
        source_id="test_id_img_fallback",
        source_type="local_image",
        path=sample_image_file,
        filename="test.png",
        extension="png",
        size_bytes=sample_image_file.stat().st_size,
        mime_type="image/png",
    )
    
    # Force Docling to fail
    def mock_parse_with_docling(*args, **kwargs):
        raise RuntimeError("Mock Docling failure")
        
    # Mock EasyOCR fallback
    def mock_extract_with_easyocr(*args, **kwargs):
        from build_your_own_rag.models import ParsedPage
        pages = [ParsedPage(page_number=1, text="Mocked EasyOCR Fallback Text", metadata={"page_number": 1})]
        meta = {"text_blocks_found": 1}
        return pages, meta
    
    import build_your_own_rag.parsing.image_parser as img_module
    monkeypatch.setattr(img_module, "_parse_with_docling", mock_parse_with_docling)
    monkeypatch.setattr(img_module, "_extract_with_easyocr", mock_extract_with_easyocr)
    
    parsed = parse_image(source, strategy=ExtractionStrategy.FAST)
    
    assert parsed.parser_name == "easyocr_fallback"
    assert parsed.status == "fallback"
    assert parsed.text == "Mocked EasyOCR Fallback Text"
    assert parsed.ocr_used is True
