from pathlib import Path

from build_your_own_rag.chunking import _split_text, _split_text_structurally, build_chunks
from build_your_own_rag.models import DocumentMetadata, ExtractionStrategy, ParsedDocument, ParsedPage, SourceDocument


def test_split_text_basic():
    text = "word " * 10
    chunks = _split_text(text, target=4, overlap=1)

    # words: 10 words total
    # target 4, overlap 1 -> step = 3
    # chunk 1: words 0-4 (4 words)
    # chunk 2: words 3-7 (4 words)
    # chunk 3: words 6-10 (4 words)

    assert len(chunks) == 3
    assert len(chunks[0].split()) == 4
    assert len(chunks[1].split()) == 4
    assert len(chunks[2].split()) == 4
    assert chunks[0].split()[-1:] == chunks[1].split()[:1]


def test_split_text_prefers_sentence_boundaries():
    text = "Alpha beta. Gamma delta. Epsilon zeta."
    chunks = _split_text(text, target=4, overlap=0)

    assert chunks == ["Alpha beta. Gamma delta.", "Epsilon zeta."]


def test_split_text_structurally_preserves_table():
    text = """This is a normal paragraph that should be kept intact.

| Header 1 | Header 2 |
|---|---|
| Row 1 | Data 1 |
| Row 2 | Data 2 |
| Row 3 | Data 3 |
| Row 4 | Data 4 |
| Row 5 | Data 5 |

Another small paragraph here."""

    # Target is very small (e.g., 5 words). The table has ~20 words.
    # The table should be preserved as a single chunk despite exceeding target.
    chunks = _split_text_structurally(text, target=5, overlap=0)

    assert len(chunks) >= 3
    # Find the chunk containing the table
    table_chunk = next(c for c in chunks if "| Header 1" in c)
    assert "| Row 5" in table_chunk
    assert "Row 1" in table_chunk


def test_split_text_structurally_prefers_paragraph_boundaries():
    text = """First paragraph stays together.

Second paragraph also stays together.

Third paragraph closes it out."""
    chunks = _split_text_structurally(text, target=5, overlap=0)

    assert chunks == [
        "First paragraph stays together.",
        "Second paragraph also stays together.",
        "Third paragraph closes it out.",
    ]


def test_split_text_structurally_prefers_markdown_header_boundaries():
    text = """# Install
Use the default setup.

## Retrieval
Tune chunks carefully."""
    chunks = _split_text_structurally(text, target=6, overlap=0)

    assert chunks == [
        "# Install\nUse the default setup.",
        "## Retrieval\nTune chunks carefully.",
    ]


def test_split_text_structurally_splits_large_paragraphs():
    large_paragraph = "word " * 50
    text = f"First block.\n\n{large_paragraph}\n\nLast block."

    chunks = _split_text_structurally(text, target=10, overlap=2)
    # First block (2 words)
    # The large paragraph (50 words) should be split into ~6 chunks of 10 words with overlap
    # Last block (2 words)

    assert len(chunks) > 3
    # Check that no chunk exceeds the target drastically (except tables, but there are no tables here)
    for c in chunks:
        # A chunk could be slightly larger due to merging logic, but shouldn't be the full 50 words
        assert len(c.split()) <= 15


def test_build_chunks_records_structural_strategy_metadata(monkeypatch):
    monkeypatch.setenv("CHUNK_TARGET_TOKENS", "350")
    monkeypatch.setenv("CHUNK_OVERLAP_TOKENS", "50")
    monkeypatch.delenv("CHUNK_OVERLAP_RATIO", raising=False)
    monkeypatch.setenv("WORD_TOKEN_RATIO", "1")

    parsed = ParsedDocument(
        source=SourceDocument(
            source_id="source-1",
            source_type="local_pdf",
            path=Path("/tmp/sample.pdf"),
            filename="sample.pdf",
            extension="pdf",
            size_bytes=10,
            mime_type="application/pdf",
        ),
        text="",
        pages=[
            ParsedPage(
                page_number=1,
                text="First paragraph has enough words to become one chunk. Second paragraph remains structured.",
            )
        ],
        metadata=DocumentMetadata(core={}, processing={}, format_specific={}),
        parser_name="pypdf_fallback",
        strategy=ExtractionStrategy.FAST,
        ocr_used=False,
    )

    chunks = build_chunks(parsed)

    chunking = chunks[0].metadata["chunking"]
    assert chunking["strategy"] == "recursive_structural"
    assert chunking["token_target"] == 350
    assert chunking["token_overlap"] == 50
    assert chunking["boundary_order"] == ["markdown_header", "paragraph", "sentence", "word"]
