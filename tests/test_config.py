from build_your_own_rag.config import DEFAULT_CHUNK_OVERLAP_TOKENS, DEFAULT_CHUNK_TARGET_TOKENS, get_settings


def test_default_chunk_target_tokens_tracks_retrieval_baseline(monkeypatch):
    monkeypatch.delenv("CHUNK_TARGET_TOKENS", raising=False)
    monkeypatch.delenv("CHUNK_OVERLAP_TOKENS", raising=False)
    monkeypatch.delenv("CHUNK_OVERLAP_RATIO", raising=False)

    settings = get_settings()

    assert DEFAULT_CHUNK_TARGET_TOKENS == 350
    assert DEFAULT_CHUNK_OVERLAP_TOKENS == 50
    assert settings.chunk_target_tokens == 350
    assert settings.chunk_overlap_tokens == 50


def test_chunk_target_tokens_can_be_overridden(monkeypatch):
    monkeypatch.setenv("CHUNK_TARGET_TOKENS", "384")
    monkeypatch.setenv("CHUNK_OVERLAP_TOKENS", "64")

    settings = get_settings()

    assert settings.chunk_target_tokens == 384
    assert settings.chunk_overlap_tokens == 64


def test_legacy_chunk_overlap_ratio_still_maps_to_tokens(monkeypatch):
    monkeypatch.setenv("CHUNK_TARGET_TOKENS", "400")
    monkeypatch.delenv("CHUNK_OVERLAP_TOKENS", raising=False)
    monkeypatch.setenv("CHUNK_OVERLAP_RATIO", "0.1")

    settings = get_settings()

    assert settings.chunk_overlap_tokens == 40
