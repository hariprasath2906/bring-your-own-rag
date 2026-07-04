from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path

from build_your_own_rag.models import SourceDocument


def inspect_local_pdf(path_value: str) -> SourceDocument:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        raise ValueError(
            "Expected an absolute PDF path. Examples: "
            "/home/user/data/sample.pdf, /Users/user/data/sample.pdf, "
            "or C:\\Users\\user\\data\\sample.pdf"
        )
    if not path.exists():
        raise FileNotFoundError(f"PDF file does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"MVP supports PDF files only, got extension: {path.suffix}")

    stat = path.stat()
    source_key = str(path.resolve())
    source_id = hashlib.sha256(source_key.encode("utf-8")).hexdigest()
    mime_type = mimetypes.guess_type(path.name)[0] or "application/pdf"

    return SourceDocument(
        source_id=source_id,
        source_type="local_pdf",
        path=path.resolve(),
        filename=path.name,
        extension=path.suffix.lower().lstrip("."),
        size_bytes=stat.st_size,
        mime_type=mime_type,
    )
