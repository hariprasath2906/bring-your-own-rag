from __future__ import annotations

from build_your_own_rag.config import get_settings
from build_your_own_rag.models import ChunkRecord, ParsedDocument


import re

def build_chunks(parsed: ParsedDocument) -> list[ChunkRecord]:
    settings = get_settings()

    # Convert token target to word target using the word-to-token ratio.
    word_target = max(1, int(settings.chunk_target_tokens / settings.word_token_ratio))
    overlap = max(0, int(word_target * settings.chunk_overlap_ratio))

    chunks: list[ChunkRecord] = []
    chunk_index = 0

    if parsed.parser_name == "docling" and parsed.text.strip():
        # Docling output is structured markdown; chunk the whole text structurally to preserve tables.
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
                            "token_target": settings.chunk_target_tokens,
                            "word_target": word_target,
                            "word_token_ratio": settings.word_token_ratio,
                            "overlap_words": overlap,
                        },
                    },
                )
            )
            chunk_index += 1
    else:
        # Fallback to page-based chunking for pypdf
        for page in parsed.pages:
            page_chunks = _split_text(page.text, target=word_target, overlap=overlap)
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
                                "token_target": settings.chunk_target_tokens,
                                "word_target": word_target,
                                "word_token_ratio": settings.word_token_ratio,
                                "overlap_words": overlap,
                            },
                        },
                    )
                )
                chunk_index += 1

    return chunks


def _split_text_structurally(text: str, target: int, overlap: int) -> list[str]:
    """Split markdown text structurally, keeping tables and paragraphs intact where possible."""
    blocks = re.split(r'\n\s*\n', text.strip())
    
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_words = 0
    
    for block in blocks:
        block = block.strip()
        if not block:
            continue
            
        block_words = len(block.split())
        is_table = block.startswith("|") and ("-|" in block or "|-" in block)
        
        if current_chunk and (current_words + block_words > target):
            chunks.append("\n\n".join(current_chunk))
            
            overlap_words = 0
            overlap_blocks = []
            for b in reversed(current_chunk):
                b_words = len(b.split())
                if overlap_words + b_words <= overlap:
                    overlap_blocks.insert(0, b)
                    overlap_words += b_words
                else:
                    if overlap > 0 and not overlap_blocks:
                        overlap_blocks.insert(0, b)
                        overlap_words += b_words
                    break
            
            current_chunk = overlap_blocks
            current_words = overlap_words
            
        if block_words > target:
            if is_table:
                # Keep tables whole even if they exceed the target
                current_chunk.append(block)
                current_words += block_words
            else:
                # If a regular paragraph is too large, split it by words
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_words = 0
                
                word_chunks = _split_text(block, target, overlap)
                for i, wc in enumerate(word_chunks):
                    if i == len(word_chunks) - 1:
                        current_chunk.append(wc)
                        current_words += len(wc.split())
                    else:
                        chunks.append(wc)
        else:
            current_chunk.append(block)
            current_words += block_words
            
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    return chunks


def _split_text(text: str, target: int, overlap: int) -> list[str]:
    """Split *text* into chunks of approximately *target* words with *overlap*."""
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


