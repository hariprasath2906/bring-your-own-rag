# Platform Support

The MVP is designed to run on Windows, macOS, and Linux.

## Recommended Runtime

Use Docker Desktop or Docker Engine for the local PostgreSQL + pgvector database.

| Platform | Recommended shell | Notes |
| --- | --- | --- |
| Windows | PowerShell | Use Windows paths for host CLI runs. Docker container paths still use Linux-style paths such as `/data/sample.pdf`. |
| macOS | zsh or bash | Apple Silicon should use native arm64 Docker builds by default. |
| Linux | bash | Native Docker Engine is recommended. |

> [!NOTE]
> For LLM Generation, you can either run Ollama natively on your host machine (Mac/Windows/Linux) or run the `ollama` Docker service via the `llm` profile (`docker compose --profile llm up -d`). Running natively is often faster on Apple Silicon Macs.

## Host Python Setup

macOS/Linux:

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

Windows Command Prompt:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
set PYTHONPATH=src
```

## Sample PDF Path

The CLI requires an absolute PDF path.

macOS/Linux:

```bash
python -m build_your_own_rag.cli inspect-source --path "$(pwd)/data/sample.pdf"
```

Windows PowerShell:

```powershell
$sample = (Resolve-Path .\data\sample.pdf).Path
python -m build_your_own_rag.cli inspect-source --path $sample
```

Windows Command Prompt:

```bat
python -m build_your_own_rag.cli inspect-source --path "%cd%\data\sample.pdf"
```

## Docker Paths

The Docker app service mounts local `./data` to container path `/data`.

Use `/data/sample.pdf` inside Docker on all host operating systems:

```bash
docker compose run --rm app python -m build_your_own_rag.cli ingest --path "/data/sample.pdf" --strategy FAST
```

Create the local data folder with the command for your shell:

macOS/Linux:

```bash
mkdir -p data
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force data
```

## CPU Dependency Strategy

This MVP is CPU-first.

- Windows/macOS/Linux host installs use `requirements.txt`.
- Docker installs CPU PyTorch and torchvision before Docling, EasyOCR, and sentence-transformers.
- Linux x86_64 Docker builds use the official PyTorch CPU wheel index.
- Linux arm64 Docker builds use PyPI because CPU wheel availability differs by architecture.

NVIDIA CUDA is not required unless you intentionally add GPU support later.
