FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        libgl1 \
        libglib2.0-0 \
        poppler-utils \
        tesseract-ocr \
        tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY requirements-cpu.txt .

# Install the CPU PyTorch stack first so Docling, EasyOCR, and
# sentence-transformers reuse it instead of pulling CUDA/NVIDIA wheels through
# transitive dependencies. The PyTorch CPU wheel index is reliable for Linux
# x86_64; Linux arm64 uses PyPI wheels.
ARG TORCH_CPU_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN set -eux; \
    arch="$(uname -m)"; \
    if [ "$arch" = "x86_64" ] || [ "$arch" = "amd64" ]; then \
        pip install --no-cache-dir --index-url "${TORCH_CPU_INDEX_URL}" -r requirements-cpu.txt; \
    else \
        pip install --no-cache-dir -r requirements-cpu.txt; \
    fi; \
    pip install --no-cache-dir -r requirements.txt

COPY src ./src

CMD ["python", "-m", "build_your_own_rag.cli", "--help"]
