from __future__ import annotations

import re

from build_your_own_rag.config import get_settings
from build_your_own_rag.models import ChunkRecord, ParsedDocument


BOUNDARY_ORDER = ["markdown_header", "paragraph", "sentence", "word"]
MARKDOWN_HEADER_RE = re.compile(r"^#{1,6}\s+")
SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+")


def build_chunks(parsed: ParsedDocument) -> list[ChunkRecord]:
    settings = get_settings()

    # Convert token target to word target using the word-to-token ratio.
    word_target = max(1, int(settings.chunk_target_tokens / settings.word_token_ratio))
    effective_overlap_tokens = min(
        max(0, settings.chunk_overlap_tokens),
        max(0, settings.chunk_target_tokens - 1),
    )
    overlap = min(
        max(0, int(effective_overlap_tokens / settings.word_token_ratio)),
        max(0, word_target - 1),
    )

    chunks: list[ChunkRecord] = []
    chunk_index = 0

    # ── Chunking strategy dispatch ─────────────────────────────────────
    # Parsers that produce a single unified text (e.g., Docling-based
    # parsers for PDF/DOCX/PPTX, or native text parsers for .md/.txt)
    # populate ``parsed.text`` with the full document content.  These
    # take the structural path which chunks the entire text while
    # preserving markdown tables.
    #
    # Parsers that only produce per-page text (e.g., pypdf fallback)
    # leave ``parsed.text`` empty and populate ``parsed.pages``.  These
    # take the per-page path which chunks each page independently.
    #
    # New parsers: populate ``parsed.text`` for full-document chunking.
    # Only use the pages-only path if your parser cannot produce
    # consolidated text (e.g., a raw PDF page extractor).
    # ──────────────────────────────────────────────────────────────────
    if parsed.text.strip():
        # Full-document text available; chunk the whole text structurally to preserve tables.
        text_chunks = _split_text_structurally(parsed.text, target=word_target, overlap=overlap)
        for content in text_chunks:
            normalized = content.strip()
            if not normalized:
                continue
            chunks.append(
                ChunkRecord(
                    source_id=parsed.source.source_id,
                    source_type=parsed.source.source_type,
                    chunk_index=chunk_index,
                    content=normalized,
                    metadata={
                        "core": parsed.metadata.core,
                        "processing": parsed.metadata.processing,
                        "format_specific": parsed.metadata.format_specific,
                        "element": {},
                        "chunking": {
                            "strategy": "recursive_structural",
                            "token_target": settings.chunk_target_tokens,
                            "token_overlap": settings.chunk_overlap_tokens,
                            "effective_token_overlap": effective_overlap_tokens,
                            "word_target": word_target,
                            "word_token_ratio": settings.word_token_ratio,
                            "overlap_words": overlap,
                            "boundary_order": BOUNDARY_ORDER,
                        },
                    },
                )
            )
            chunk_index += 1
    else:
        # Fallback to page-scoped structural chunking for pypdf.
        for page in parsed.pages:
            page_chunks = _split_text_structurally(page.text, target=word_target, overlap=overlap)
            for content in page_chunks:
                normalized = content.strip()
                if not normalized:
                    continue
                chunks.append(
                    ChunkRecord(
                        source_id=parsed.source.source_id,
                        source_type=parsed.source.source_type,
                        chunk_index=chunk_index,
                        content=normalized,
                        metadata={
                            "core": parsed.metadata.core,
                            "processing": parsed.metadata.processing,
                            "format_specific": parsed.metadata.format_specific,
                            "element": {
                                "page_number": page.page_number,
                                "section_hierarchy": None,
                                "coordinates": None,
                                "style_name": None,
                                "formatting": None,
                                "language": "en",
                            },
                            "chunking": {
                                "strategy": "recursive_structural",
                                "token_target": settings.chunk_target_tokens,
                                "token_overlap": settings.chunk_overlap_tokens,
                                "effective_token_overlap": effective_overlap_tokens,
                                "word_target": word_target,
                                "word_token_ratio": settings.word_token_ratio,
                                "overlap_words": overlap,
                                "boundary_order": BOUNDARY_ORDER,
                            },
                        },
                    )
                )
                chunk_index += 1

    return chunks


def _split_text_structurally(text: str, target: int, overlap: int) -> list[str]:
    """Split text using markdown, paragraph, sentence, then word boundaries."""
    blocks = _split_markdown_blocks(text)

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_words = 0

    for block in blocks:
        block_words = _word_count(block)
        is_table = _is_markdown_table(block)

        if current_chunk and (current_words + block_words > target):
            chunks.append("\n\n".join(current_chunk))
            overlap_blocks, overlap_words = _overlap_tail(current_chunk, overlap)
            current_chunk = overlap_blocks
            current_words = overlap_words

            if current_chunk and current_words + block_words > target:
                current_chunk = []
                current_words = 0

        if block_words > target:
            if is_table:
                # Keep tables whole even if they exceed the target.
                current_chunk.append(block)
                current_words += block_words
            else:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_words = 0

                word_chunks = _split_text(block, target, overlap)
                for i, wc in enumerate(word_chunks):
                    if i == len(word_chunks) - 1:
                        current_chunk.append(wc)
                        current_words += _word_count(wc)
                    else:
                        chunks.append(wc)
        else:
            current_chunk.append(block)
            current_words += block_words

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def _split_text(text: str, target: int, overlap: int) -> list[str]:
    """Split text by sentence boundaries before falling back to word windows."""
    sentences = _split_sentences(text)
    if len(sentences) > 1:
        return _pack_units(sentences, target=target, overlap=overlap, separator=" ")
    return _split_words(text, target=target, overlap=overlap)


def _split_words(text: str, target: int, overlap: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    if len(words) <= target:
        return [" ".join(words)]

    chunks: list[str] = []
    step = max(1, target - overlap)
    start = 0
    while start < len(words):
        end = min(len(words), start + target)
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += step
    return chunks


def _split_markdown_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []

    for raw_line in text.strip().splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            continue

        if MARKDOWN_HEADER_RE.match(line) and current:
            blocks.append("\n".join(current).strip())
            current = []

        current.append(line)

    if current:
        blocks.append("\n".join(current).strip())

    return [block for block in blocks if block]


def _split_sentences(text: str) -> list[str]:
    parts = [part.strip() for part in SENTENCE_BOUNDARY_RE.split(text.strip())]
    return [part for part in parts if part]


def _pack_units(units: list[str], target: int, overlap: int, separator: str) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for unit in units:
        unit_words = _word_count(unit)
        if unit_words > target:
            if current:
                chunks.append(separator.join(current))
                current = []
                current_words = 0
            chunks.extend(_split_words(unit, target=target, overlap=overlap))
            continue

        if current and current_words + unit_words > target:
            chunks.append(separator.join(current))
            current, current_words = _overlap_tail(current, overlap)
            if current and current_words + unit_words > target:
                current = []
                current_words = 0

        current.append(unit)
        current_words += unit_words

    if current:
        chunks.append(separator.join(current))

    return chunks


def _overlap_tail(units: list[str], overlap: int) -> tuple[list[str], int]:
    if overlap <= 0 or not units:
        return [], 0

    selected: list[str] = []
    selected_words = 0
    for unit in reversed(units):
        unit_words = _word_count(unit)
        if selected_words + unit_words <= overlap:
            selected.insert(0, unit)
            selected_words += unit_words
            continue
        break

    if selected:
        return selected, selected_words

    words = units[-1].split()
    tail = " ".join(words[-overlap:])
    return [tail], _word_count(tail)


def _is_markdown_table(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return bool(lines) and lines[0].startswith("|") and any("-|" in line or "|-" in line for line in lines[:3])


def _word_count(text: str) -> int:
    return len(text.split())

