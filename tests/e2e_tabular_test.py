import subprocess
import time
import sys
from pathlib import Path

def run_cmd(cmd, env=None):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
        raise RuntimeError(f"Command failed: {cmd}")
    return result.stdout

def test_native_e2e():
    print("--- Starting Native E2E Test ---")
    base_dir = Path(__file__).parent.parent
    csv_path = base_dir / "data" / "test_docs" / "complex_data.csv"
    
    # Ingest the CSV file natively
    ingest_cmd = [
        sys.executable, "-m", "build_your_own_rag.cli", "ingest",
        "--path", str(csv_path)
    ]
    stdout = run_cmd(ingest_cmd)
    assert '"status": "active"' in stdout or "chunk_count" in stdout, "Ingestion failed"
    
    # Retrieve chunks
    retrieve_cmd = [
        sys.executable, "-m", "build_your_own_rag.cli", "retrieve",
        "--query", "widget B multiline"
    ]
    stdout = run_cmd(retrieve_cmd)
    assert "Widget B" in stdout and "Multiline" in stdout, "Retrieval did not return the expected CSV chunk"
    print("Native E2E Test Passed!\n")

def test_docker_ollama_e2e():
    print("--- Starting Docker + Ollama E2E Test ---")
    base_dir = Path(__file__).parent.parent
    xlsx_path = base_dir / "data" / "test_docs" / "complex_data.xlsx"
    
    # Ingest the XLSX file via Docker
    ingest_cmd = [
        "docker", "compose", "run", "--rm", "app",
        "python", "-m", "build_your_own_rag.cli", "ingest",
        "--path", f"/app/data/test_docs/{xlsx_path.name}"
    ]
    stdout = run_cmd(ingest_cmd)
    assert '"status": "active"' in stdout or "chunk_count" in stdout, "Docker ingestion failed"
    
    # Query Ollama to generate an answer
    ask_cmd = [
        "docker", "compose", "run", "--rm", "-e", "OLLAMA_BASE_URL=http://host.docker.internal:11434", "app",
        "python", "-m", "build_your_own_rag.cli", "ask",
        "--query", "Which employee is in the Engineering department?",
        "--model", "granite3.3:8b"
    ]
    
    print("Asking Ollama (granite model) via Docker...")
    stdout = run_cmd(ask_cmd)
    
    # Check that it generated a response referencing Alice Smith
    assert "Alice Smith" in stdout, "LLM did not extract Alice Smith from the XLSX data"
    print("Docker + Ollama E2E Test Passed!\n")

if __name__ == "__main__":
    import sys
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "native":
            test_native_e2e()
        elif len(sys.argv) > 1 and sys.argv[1] == "docker":
            test_docker_ollama_e2e()
        else:
            test_native_e2e()
            test_docker_ollama_e2e()
            print("ALL E2E TESTS PASSED!")
    except Exception as e:
        print(f"E2E TEST FAILED: {e}")
        exit(1)
