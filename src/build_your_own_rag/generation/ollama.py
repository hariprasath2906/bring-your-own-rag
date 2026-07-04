import json
import time
import urllib.request
import urllib.error
from typing import Any

from build_your_own_rag.config import get_settings
from build_your_own_rag.models import GenerationResult, RetrievalResult
from build_your_own_rag.utils.logger import get_logger

logger = get_logger(__name__)

class GenerationError(RuntimeError):
    """Raised when LLM generation fails."""

def build_prompt(query: str, context_chunks: list[RetrievalResult]) -> str:
    """Builds the RAG prompt from the retrieved chunks."""
    context_blocks = []
    for idx, chunk in enumerate(context_chunks, start=1):
        # Extract page number if available
        page_num = chunk.metadata.get("element", {}).get("page_number", "Unknown")
        source_id = chunk.metadata.get("core", {}).get("source_id", "Unknown")
        
        context_blocks.append(f"--- Document Source {idx} (Page: {page_num}, Source ID: {source_id}) ---\n{chunk.content}")
        
    context_str = "\n\n".join(context_blocks)
    
    return f"""You are a helpful and precise assistant. Answer the user's question based ONLY on the following context.
If the context does not contain the answer, say "I don't have enough information in the provided context to answer that."

Context:
{context_str}

Question: {query}
Answer:"""

def generate(query: str, context_chunks: list[RetrievalResult], override_model: str | None = None) -> GenerationResult:
    """Generates an answer using the local Ollama API."""
    settings = get_settings()
    model = override_model or settings.ollama_model
    
    prompt = build_prompt(query, context_chunks)
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": settings.ollama_temperature
        }
    }
    
    url = f"{settings.ollama_base_url}/api/generate"
    req = urllib.request.Request(
        url, 
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    
    logger.info("Calling Ollama API", extra={"extra_info": {"model": model, "url": url}})
    
    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            answer = response_data.get("response", "")
    except urllib.error.URLError as exc:
        error_msg = f"Failed to connect to Ollama at {url}: {exc}"
        logger.error(error_msg)
        raise GenerationError(error_msg) from exc
    except Exception as exc:
        error_msg = f"Unexpected error calling Ollama: {exc}"
        logger.error(error_msg)
        raise GenerationError(error_msg) from exc
        
    duration_ms = int((time.time() - start_time) * 1000)
    logger.info("Ollama generation complete", extra={"extra_info": {"duration_ms": duration_ms, "model": model}})
    
    return GenerationResult(
        answer=answer.strip(),
        model=model,
        query=query,
        context_chunks=context_chunks,
        retrieval_mode="unknown", # this will be populated by the pipeline
        duration_ms=duration_ms
    )
