# Build Your Own RAG

Cross-platform local MVP for a PDF-first RAG ingestion and retrieval pipeline. The project is intended to run on Windows, macOS, and Linux.

The initial flow is:

```text
absolute PDF path -> parse -> metadata -> chunk -> embed -> PostgreSQL pgvector -> hybrid retrieval -> Ollama LLM -> generated answer
```

## Local Runtime

Start PostgreSQL with pgvector (and optionally Ollama) on any supported OS:

```bash
docker compose --profile llm up -d
docker compose exec postgres psql -U rag_user -d rag_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

If your Docker install exposes the legacy command, use `docker-compose` in place of `docker compose`.

### 1. Configuration (.env)

Copy the example configuration:

```bash
cp .env.example .env
```

**CRITICAL:** Depending on how you run the CLI, you must set the `POSTGRES_HOST` and `OLLAMA_BASE_URL` in your `.env` file correctly:

- **If running Native (Host Terminal):**
  - `POSTGRES_HOST=localhost`
  - `OLLAMA_BASE_URL=http://localhost:11434`
- **If running via Docker (`docker compose run app`):**
  - `POSTGRES_HOST=postgres`
  - `OLLAMA_BASE_URL=http://host.docker.internal:11434` (on Mac/Windows)

Retrieval chunking is controlled by `CHUNK_TARGET_TOKENS`, `CHUNK_OVERLAP_TOKENS`, and `WORD_TOKEN_RATIO`.
The default baseline is `CHUNK_TARGET_TOKENS=350` with `CHUNK_OVERLAP_TOKENS=50` for `BAAI/bge-base-en-v1.5`. This keeps chunks below the embedding model's 512-token input window while preserving enough context across boundaries for retrieval.

Chunking is structural first: markdown headers, paragraph breaks, and sentence boundaries are preferred before falling back to word windows. When tuning retrieval quality, try values such as `300/50`, `350/50`, and `384/64`, then re-run ingestion so stored chunks and embeddings are rebuilt with the new setting. `CHUNK_OVERLAP_RATIO` is still accepted as a legacy fallback when `CHUNK_OVERLAP_TOKENS` is not set.

Parent-child retrieval is a future option if we later want smaller embedded child chunks with larger parent context passed to generation. That would be a separate retrieval/schema change, not part of the current baseline.

---

### 2. Run Migrations

Database schemas must be created before ingestion. 

#### Via Docker (Recommended)

```bash
docker compose run --rm app python -m build_your_own_rag.db.migrate
```

Install Python dependencies on host only if you want to run outside.

### 3. Execution (Natively via Host Terminal)

**Prerequisites:** You must have installed the dependencies (`pip install -r requirements.txt`), exported the python path (`export PYTHONPATH=src`), and set your `.env` to use `localhost`.

macOS/Linux shell:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export PYTHONPATH=src
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:PYTHONPATH = "src"
```

On Apple Silicon macOS and most CPU-only host installs, normal `python -m pip install -r requirements.txt` should not require NVIDIA CUDA packages. For Docker/Linux builds, the Dockerfile preinstalls CPU PyTorch and torchvision before installing Docling, EasyOCR, and sentence-transformers.

`easyocr` is declared as a direct dependency because Docling needs it for OCR-backed parsing. Install `requirements.txt` before using `HI_RES` or `OCR_ONLY`; otherwise those strategies cannot perform OCR extraction reliably. The `FAST` strategy does not use OCR.

Run migrations:

```bash
python -m build_your_own_rag.db.migrate
```

Place a sample PDF at `data/sample.pdf`, then run the commands for your shell.

macOS/Linux shell:

```bash
mkdir -p data
python -m build_your_own_rag.cli inspect-source --path "$(pwd)/data/sample.pdf"
python -m build_your_own_rag.cli parse --path "$(pwd)/data/sample.pdf" --strategy FAST --show-metadata
python -m build_your_own_rag.cli chunk --path "$(pwd)/data/sample.pdf" --strategy FAST
python -m build_your_own_rag.cli embed --path "$(pwd)/data/sample.pdf" --strategy FAST --limit 2
python -m build_your_own_rag.cli ingest --path "$(pwd)/data/sample.pdf" --strategy FAST
python -m build_your_own_rag.cli retrieve --query "What is this document about?" --top-k 5 --mode hybrid
python -m build_your_own_rag.cli ask --query "What is this document about?" --show-context
python -m build_your_own_rag.cli search-keyword --query "specific term" --top-k 5
python -m build_your_own_rag.cli smoke-test --path "$(pwd)/data/sample.pdf" --query "test query"
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force data
$sample = (Resolve-Path .\data\sample.pdf).Path
python -m build_your_own_rag.cli inspect-source --path $sample
python -m build_your_own_rag.cli parse --path $sample --strategy FAST --show-metadata
python -m build_your_own_rag.cli chunk --path $sample --strategy FAST
python -m build_your_own_rag.cli embed --path $sample --strategy FAST --limit 2
python -m build_your_own_rag.cli ingest --path $sample --strategy FAST
python -m build_your_own_rag.cli retrieve --query "What is this document about?" --top-k 5 --mode hybrid
python -m build_your_own_rag.cli ask --query "What is this document about?" --show-context
python -m build_your_own_rag.cli search-keyword --query "specific term" --top-k 5
python -m build_your_own_rag.cli smoke-test --path $sample --query "test query"
```

Run inside Docker app container:

macOS/Linux:

```bash
mkdir -p data
docker compose build app
docker compose run --rm app python -m build_your_own_rag.db.migrate
docker compose run --rm app python -m build_your_own_rag.cli inspect-source --path "/data/sample.pdf"
docker compose run --rm app python -m build_your_own_rag.cli parse --path "/data/sample.pdf" --strategy FAST --show-metadata
docker compose run --rm app python -m build_your_own_rag.cli chunk --path "/data/sample.pdf" --strategy FAST
docker compose run --rm app python -m build_your_own_rag.cli embed --path "/data/sample.pdf" --strategy FAST --limit 2
docker compose run --rm app python -m build_your_own_rag.cli ingest --path "/data/sample.pdf" --strategy FAST
docker compose run --rm app python -m build_your_own_rag.cli retrieve --query "What is this document about?" --top-k 5 --mode hybrid
docker compose run --rm app python -m build_your_own_rag.cli ask --query "What is this document about?" --show-context
docker compose run --rm app python -m build_your_own_rag.cli search-keyword --query "specific term" --top-k 5
docker compose run --rm app python -m build_your_own_rag.cli smoke-test --path "/data/sample.pdf" --query "test query"
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force data
docker compose build app
docker compose run --rm app python -m build_your_own_rag.db.migrate
docker compose run --rm app python -m build_your_own_rag.cli inspect-source --path "/data/sample.pdf"
docker compose run --rm app python -m build_your_own_rag.cli parse --path "/data/sample.pdf" --strategy FAST --show-metadata
docker compose run --rm app python -m build_your_own_rag.cli chunk --path "/data/sample.pdf" --strategy FAST
docker compose run --rm app python -m build_your_own_rag.cli embed --path "/data/sample.pdf" --strategy FAST --limit 2
docker compose run --rm app python -m build_your_own_rag.cli ingest --path "/data/sample.pdf" --strategy FAST
docker compose run --rm app python -m build_your_own_rag.cli retrieve --query "What is this document about?" --top-k 5 --mode hybrid
docker compose run --rm app python -m build_your_own_rag.cli ask --query "What is this document about?" --show-context
docker compose run --rm app python -m build_your_own_rag.cli search-keyword --query "specific term" --top-k 5
docker compose run --rm app python -m build_your_own_rag.cli smoke-test --path "/data/sample.pdf" --query "test query"
```

For dependency-light plumbing checks only, set `USE_HASH_EMBEDDINGS=1`. Real MVP validation should use the sentence-transformers model.

## Public Docs

- [Architecture](docs/architecture.md)
- [Local MVP Guide](docs/local-mvp.md)
- [Platform Support](docs/platform-support.md)
- [Troubleshooting](docs/troubleshooting.md)

## Notes

- Docling and sentence-transformers are intentionally installed through dependencies, not vendored into this repo.
- EasyOCR is installed as a direct dependency for Docling `HI_RES` and `OCR_ONLY` extraction strategies.
- This MVP is CPU-first. NVIDIA CUDA packages are not required for normal Windows, macOS, or Linux CPU local runs.
- The local database is PostgreSQL with pgvector. It is functionally close enough for MVP validation but not identical to Aurora PostgreSQL.
- S3/SNS/SQS, ECS Fargate, Aurora production sizing, and document-level ACLs are deferred.
