from build_your_own_rag.generation.ollama import build_prompt
from build_your_own_rag.models import RetrievalResult

def test_build_prompt():
    chunks = [
        RetrievalResult(
            chunk_id=1,
            content="This is the first piece of context.",
            metadata={"element": {"page_number": 1}, "core": {"source_id": "abc-123"}},
        ),
        RetrievalResult(
            chunk_id=2,
            content="This is the second piece of context.",
            metadata={"element": {"page_number": 2}, "core": {"source_id": "abc-123"}},
        )
    ]
    
    query = "What is the context?"
    prompt = build_prompt(query, chunks)
    
    # Assertions to ensure formatting is correct
    assert "--- Document Source 1 (Page: 1, Source ID: abc-123) ---" in prompt
    assert "This is the first piece of context." in prompt
    assert "--- Document Source 2 (Page: 2, Source ID: abc-123) ---" in prompt
    assert "This is the second piece of context." in prompt
    assert f"Question: {query}" in prompt
    assert prompt.endswith("Answer:")
