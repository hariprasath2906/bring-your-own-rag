from build_your_own_rag.retrieval.hybrid import _rrf_merge
from build_your_own_rag.models import RetrievalResult

def test_rrf_merge_ranks_correctly():
    # Setup mock rows from vector and keyword search
    vector_rows = [
        {"chunk_id": 1, "content": "A", "metadata": {}, "vector_score": 0.9},
        {"chunk_id": 2, "content": "B", "metadata": {}, "vector_score": 0.8},
        {"chunk_id": 3, "content": "C", "metadata": {}, "vector_score": 0.7},
    ]
    
    keyword_rows = [
        {"chunk_id": 2, "content": "B", "metadata": {}, "keyword_score": 10.5},
        {"chunk_id": 1, "content": "A", "metadata": {}, "keyword_score": 8.2},
        {"chunk_id": 4, "content": "D", "metadata": {}, "keyword_score": 5.0},
    ]
    
    results = _rrf_merge(vector_rows, keyword_rows)
    
    # Assertions
    assert len(results) == 4
    
    # Chunk 2 should likely win because it's rank 1 in keyword and rank 2 in vector
    # Chunk 1 is rank 1 in vector and rank 2 in keyword
    # The scores should be combined properly.
    assert results[0].chunk_id in (1, 2)
    assert results[1].chunk_id in (1, 2)
    
    # Check that both scores are populated for items present in both
    chunk2 = next(r for r in results if r.chunk_id == 2)
    assert chunk2.vector_score == 0.8
    assert chunk2.keyword_score == 10.5
    assert chunk2.rrf_score is not None
    assert "vector_rank" in chunk2.rank_details
    assert "keyword_rank" in chunk2.rank_details

def test_rrf_merge_disjoint_sets():
    vector_rows = [
        {"chunk_id": 1, "content": "A", "metadata": {}, "vector_score": 0.9},
    ]
    
    keyword_rows = [
        {"chunk_id": 2, "content": "B", "metadata": {}, "keyword_score": 10.5},
    ]
    
    results = _rrf_merge(vector_rows, keyword_rows)
    
    assert len(results) == 2
    
    chunk1 = next(r for r in results if r.chunk_id == 1)
    assert chunk1.vector_score == 0.9
    assert chunk1.keyword_score is None
    
    chunk2 = next(r for r in results if r.chunk_id == 2)
    assert chunk2.vector_score is None
    assert chunk2.keyword_score == 10.5
