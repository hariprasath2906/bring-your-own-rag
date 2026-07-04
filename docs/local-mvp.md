# Local MVP Guide

## Start Database

```bash
docker compose --profile llm up -d
```

If needed, use:

```bash
docker-compose --profile llm up -d
```

## Configure Environment

Before running any python commands natively or via docker, you **must** configure your `.env` file to match your execution environment. 

Copy `.env.example` to `.env` and set:

- **If running Native (Host Terminal):**
  - `POSTGRES_HOST=localhost`
  - `OLLAMA_BASE_URL=http://localhost:11434`
- **If running via Docker (`docker compose run app`):**
  - `POSTGRES_HOST=postgres`
  - `OLLAMA_BASE_URL=http://host.docker.internal:11434` (on Mac/Windows)

---

## Run Migrations

macOS/Linux:

```bash
export PYTHONPATH=src
python -m build_your_own_rag.db.migrate
```

Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m build_your_own_rag.db.migrate
```

## Dependency Strategy

For host execution on Windows, macOS, or Linux:

```bash
python -m pip install -r requirements.txt
```

For Docker/Linux CPU execution, the Dockerfile installs PyTorch before `requirements.txt`. Linux x86_64 uses the official PyTorch CPU wheel index. Linux arm64 uses PyPI because wheel availability differs by architecture. This prevents accidental NVIDIA CUDA dependency downloads when the MVP is intended to run on CPU.

## Run Pipeline

Copy any PDF to `data/sample.pdf`.

macOS/Linux:

```bash
python -m build_your_own_rag.cli inspect-source --path "$(pwd)/data/sample.pdf"
python -m build_your_own_rag.cli parse --path "$(pwd)/data/sample.pdf" --strategy FAST --show-metadata
python -m build_your_own_rag.cli chunk --path "$(pwd)/data/sample.pdf" --strategy FAST
python -m build_your_own_rag.cli ingest --path "$(pwd)/data/sample.pdf" --strategy FAST
python -m build_your_own_rag.cli retrieve --query "What is this document about?" --top-k 5 --mode hybrid
python -m build_your_own_rag.cli ask --query "What is this document about?" --show-context
```

Windows PowerShell:

```powershell
$sample = (Resolve-Path .\data\sample.pdf).Path
python -m build_your_own_rag.cli inspect-source --path $sample
python -m build_your_own_rag.cli parse --path $sample --strategy FAST --show-metadata
python -m build_your_own_rag.cli chunk --path $sample --strategy FAST
python -m build_your_own_rag.cli ingest --path $sample --strategy FAST
python -m build_your_own_rag.cli retrieve --query "What is this document about?" --top-k 5 --mode hybrid
python -m build_your_own_rag.cli ask --query "What is this document about?" --show-context
```

## Docker App

macOS/Linux:

```bash
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
