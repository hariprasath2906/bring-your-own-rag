import pytest

from build_your_own_rag.models import ExtractionStrategy
from build_your_own_rag.parsing import docling_parser
from build_your_own_rag.parsing.docling_parser import PdfParseError, _ensure_easyocr_available
from build_your_own_rag.source import inspect_local_pdf


def test_ocr_strategy_requires_easyocr(monkeypatch):
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None)

    with pytest.raises(RuntimeError, match="OCR_ONLY extraction requires EasyOCR"):
        _ensure_easyocr_available(ExtractionStrategy.OCR_ONLY)


def test_ocr_strategy_allows_installed_easyocr(monkeypatch):
    monkeypatch.setattr("importlib.util.find_spec", lambda name: object())

    _ensure_easyocr_available(ExtractionStrategy.HI_RES)


def test_ocr_strategy_does_not_silently_fallback(tmp_path, monkeypatch):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    source = inspect_local_pdf(str(pdf_path))

    def fail_docling(source, strategy):
        raise RuntimeError("HI_RES extraction requires EasyOCR")

    monkeypatch.setattr(docling_parser, "_parse_with_docling", fail_docling)

    with pytest.raises(PdfParseError, match="HI_RES extraction failed"):
        docling_parser.parse_pdf(source, ExtractionStrategy.HI_RES)
