# Troubleshooting

## `docker compose` is unavailable

Use `docker-compose` instead. Some Docker installs expose the legacy command.

## Module import fails on host Python

Set `PYTHONPATH` to `src`.

macOS/Linux:

```bash
export PYTHONPATH=src
```

Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
```

Windows Command Prompt:

```bat
set PYTHONPATH=src
```

## Docling is not installed

Install dependencies:

```bash
pip install -r requirements.txt
```

Or run through the Docker app image.

## EasyOCR is missing for `HI_RES` or `OCR_ONLY`

Docling uses EasyOCR for OCR-backed extraction strategies, but EasyOCR is not guaranteed to arrive through Docling's default dependency set. This project declares `easyocr` directly in `requirements.txt`.

Install or refresh dependencies:

```bash
python -m pip install -r requirements.txt
```

For Docker/Linux CPU builds, keep the CPU-first preinstall before `requirements.txt` so EasyOCR's PyTorch stack stays CPU-oriented:

```bash
python -m pip install --index-url https://download.pytorch.org/whl/cpu -r requirements-cpu.txt
python -m pip install -r requirements.txt
```

If OCR is not needed, use `--strategy FAST`.

## Embedding model download fails

The real MVP uses `BAAI/bge-base-en-v1.5`. First run requires network access to download the model unless it is already cached.

For plumbing-only checks:

```bash
USE_HASH_EMBEDDINGS=1 python -m build_your_own_rag.cli embed --path "$(pwd)/data/sample.pdf"
```

Do not use hash embeddings for final retrieval validation.

## CUDA packages are being downloaded

This MVP does not need NVIDIA CUDA on Windows, macOS, Linux CPU-only hosts, or CPU-only Docker runs.

Check these points:

- Use your host's native Docker architecture where possible.
- Do not force `linux/amd64` on Apple Silicon unless intentionally testing x86_64.
- In Docker, keep the CPU-first install in the Dockerfile:

```bash
python -m pip install --index-url https://download.pytorch.org/whl/cpu -r requirements-cpu.txt
pip install -r requirements.txt
```

If CUDA packages still appear, inspect which package requested them:

```bash
pip freeze | grep -E "torch|nvidia|cuda|cudnn"
```

For final MVP validation, use CPU PyTorch plus the real sentence-transformers model. Use `USE_HASH_EMBEDDINGS=1` only to test wiring without model downloads.

## Database Connection Refused (`psycopg.OperationalError`)

If you see connection refused or timeout errors when running the CLI:
1. Ensure the PostgreSQL container is running: `docker compose ps`
2. If it's restarting, check logs: `docker compose logs postgres`
3. Ensure you have exposed the correct port (5432) in your `docker-compose.yml` or check your `POSTGRES_HOST` / `POSTGRES_PORT` environment variables.

## Port 5432 Already in Use

If `docker compose up -d postgres` fails with a port conflict on 5432:
- You likely have a local PostgreSQL instance running. 
- **Fix:** Either stop your local PostgreSQL service (`sudo systemctl stop postgresql` on Linux, or via Services on Windows), OR change the host port mapping in `docker-compose.yml` (e.g. `"5433:5432"`) and set `POSTGRES_PORT=5433` in your `.env` file.

## Migration Failures

If `python -m build_your_own_rag.db.migrate` fails:
- Ensure the database is accessible (see above).
- If the error states that tables already exist, migrations might have been run partially. You can connect to the DB and drop the schema if it's safe to do so: `docker compose exec postgres psql -U rag_user -d rag_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"` and re-run migrations.

## `pgvector` Extension Not Available

If you see `ERROR: extension "vector" is not available` during migration or insertion:
- Ensure you created the extension inside the database first:
  ```bash
  docker compose exec postgres psql -U rag_user -d rag_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
  ```
- Make sure you are using the `pgvector/pgvector:pg16` Docker image, not the standard `postgres:16` image.

## Memory Issues with Large PDFs / Embedding Model

If the process is killed (OOM - Out of Memory) during parsing or embedding:
- **Docling Memory:** Parsing large, image-heavy PDFs with OCR requires significant RAM. Use `strategy=FAST` to disable OCR and table structure analysis if you're constrained on memory.
- **Embedding Memory:** The `bge-base-en-v1.5` model requires ~500MB of RAM. If you are processing thousands of chunks, the batch embedding might consume too much memory. Consider using a smaller model (`bge-small-en-v1.5`) or limiting the batch size.
- **Docker Limits:** Increase the memory limit allocated to Docker Desktop (Preferences -> Resources -> Memory). Set it to at least 4GB, ideally 8GB.

## Docker Volume Permission Errors on Linux

If PostgreSQL fails to start on Linux with a `Permission denied` error for `/var/lib/postgresql/data`:
- Docker volumes on Linux sometimes conflict with the container's user ID.
- **Fix:** Either delete the named volume `docker volume rm rag_postgres_data` and let Docker recreate it, or use `docker compose` with user namespacing / chown: `sudo chown -R 999:999 ./.volumes/postgres` (if using bind mounts).

## Ollama Connection Refused or Not Found

If you run `python -m build_your_own_rag.cli ask ...` and get a `GenerationError: Failed to connect to Ollama`:
1. Ensure Ollama is running natively or via docker (`docker compose --profile llm up -d`).
2. Verify the model is downloaded: `ollama list`. If your `OLLAMA_MODEL` is `granite3.3:8b`, run `ollama pull granite3.3:8b`.
3. Check `OLLAMA_BASE_URL` in your `.env` file if you are running it on a different port or host.
