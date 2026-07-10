from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path

from build_your_own_rag.models import SourceDocument

# ── Supported extension registry ─────────────────────────────────────────
# Maps lowercase extension (including dot) to source_type and default MIME.
# New formats register here when their parser iteration is added.
SUPPORTED_EXTENSIONS: dict[str, dict[str, str]] = {
    ".pdf": {"source_type": "local_pdf", "mime_type": "application/pdf"},
    ".md": {"source_type": "local_md", "mime_type": "text/markdown"},
}


def inspect_local_file(path_value: str) -> SourceDocument:
    """Validate any supported local file path and return a ``SourceDocument``.

    Raises ``ValueError`` for unsupported extensions or non-absolute paths.
    Raises ``FileNotFoundError`` if the file does not exist.
    """
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        raise ValueError(
            "Expected an absolute file path. Examples: "
            "/home/user/data/sample.pdf, /Users/user/data/report.docx, "
            "or C:\\Users\\user\\data\\data.csv"
        )
    if not path.exists():
        raise FileNotFoundError(f"File does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS.keys()))
        raise ValueError(
            f"Unsupported file extension: '{ext}'. Supported extensions: {supported}"
        )

    info = SUPPORTED_EXTENSIONS[ext]
    stat = path.stat()
    source_key = str(path.resolve())
    source_id = hashlib.sha256(source_key.encode("utf-8")).hexdigest()
    mime_type = mimetypes.guess_type(path.name)[0] or info["mime_type"]

    return SourceDocument(
        source_id=source_id,
        source_type=info["source_type"],
        path=path.resolve(),
        filename=path.name,
        extension=ext.lstrip("."),
        size_bytes=stat.st_size,
        mime_type=mime_type,
    )


def inspect_local_pdf(path_value: str) -> SourceDocument:
    """Backward-compatible wrapper — validates that the file is a PDF.

    Delegates to ``inspect_local_file`` after confirming the extension.
    """
    path = Path(path_value).expanduser()
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, got extension: {path.suffix}")
    return inspect_local_file(path_value)
