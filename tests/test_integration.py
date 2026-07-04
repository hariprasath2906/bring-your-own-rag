import os
import subprocess
import unittest
import sys

class BaseCLITests(unittest.TestCase):
    env_vars = {}
    use_docker = False

    def setUp(self):
        self.pdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "sample.pdf"))
        # Use docker path if running via docker
        if self.use_docker:
            self.pdf_path = "/data/sample.pdf"

        # Create sample PDF if it does not exist
        if not os.path.exists(os.path.join(os.path.dirname(__file__), "..", "data", "sample.pdf")):
            script_path = os.path.join(os.path.dirname(__file__), "..", "data", "generate_sample.py")
            if os.path.exists(script_path):
                subprocess.run([sys.executable, script_path], check=True)

    def run_cli_command(self, args):
        env = os.environ.copy()
        env.update(self.env_vars)
        env["PYTHONPATH"] = "src"
        
        # When running native, skip some commands that require the real model unless we want to wait. 
        # But for an extensive test, we let them run. We can use USE_HASH_EMBEDDINGS=1 to speed up testing if needed.
        env["USE_HASH_EMBEDDINGS"] = "1"
        
        if self.use_docker:
            # We don't need hash embeddings in docker if the image already has the model, but it's faster.
            cmd = ["docker", "compose", "run", "--rm"]
            # pass environment variables to docker
            for k, v in self.env_vars.items():
                cmd.extend(["-e", f"{k}={v}"])
            cmd.extend(["app", "python", "-m"])
            cmd.extend(args)
        else:
            cmd = [sys.executable, "-m"]
            cmd.extend(args)
            
        print(f"\\nRunning: {' '.join(cmd)}")
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, msg=f"Command failed with {result.returncode}.\\nSTDOUT: {result.stdout}\\nSTDERR: {result.stderr}")
        return result.stdout

    def test_01_migrate(self):
        self.run_cli_command(["build_your_own_rag.db.migrate"])

    def test_02_inspect_source(self):
        out = self.run_cli_command(["build_your_own_rag.cli", "inspect-source", "--path", self.pdf_path])
        self.assertIn("sample.pdf", out)

    def test_03_chunk(self):
        out = self.run_cli_command(["build_your_own_rag.cli", "chunk", "--path", self.pdf_path, "--strategy", "FAST"])
        self.assertIn("chunk_count", out)

    def test_04_embed(self):
        out = self.run_cli_command(["build_your_own_rag.cli", "embed", "--path", self.pdf_path, "--strategy", "FAST"])
        self.assertIn("embedding_preview", out)

    def test_05_ingest(self):
        self.run_cli_command(["build_your_own_rag.cli", "ingest", "--path", self.pdf_path, "--strategy", "FAST"])

    def test_06_search_keyword(self):
        out = self.run_cli_command(["build_your_own_rag.cli", "search-keyword", "--query", "test", "--top-k", "1"])
        self.assertIn("keyword_score", out)

    def test_07_retrieve(self):
        out = self.run_cli_command(["build_your_own_rag.cli", "retrieve", "--query", "test", "--top-k", "1", "--mode", "hybrid"])
        self.assertIn("rrf_score", out)

    def test_08_ask(self):
        out = self.run_cli_command(["build_your_own_rag.cli", "ask", "--query", "What is this document about?", "--show-context"])
        self.assertIn("answer", out)


class TestNativeCLI(BaseCLITests):
    use_docker = False
    env_vars = {
        "POSTGRES_HOST": "localhost",
        "OLLAMA_BASE_URL": "http://localhost:11434"
    }


class TestDockerCLI(BaseCLITests):
    use_docker = True
    env_vars = {
        # Using host.docker.internal to reach the native ollama on the host
        "OLLAMA_BASE_URL": "http://host.docker.internal:11434"
    }


if __name__ == "__main__":
    unittest.main()
