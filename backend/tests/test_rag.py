"""Corpus retrieval sanity."""

from app.services.rag import Retriever


def test_corpus_loads_chunks():
    r = Retriever()
    assert len(r.chunks) >= 10
    assert all(c.source for c in r.chunks)


def test_placeholder_headers_excluded():
    r = Retriever()
    assert not any("[PLACEHOLDER" in c.text for c in r.chunks)


def test_retrieve_paddy_pest_finds_planthopper():
    r = Retriever()
    chunks = r.retrieve("paddy brown planthopper high humidity", k=4)
    assert chunks, "expected at least one hit"
    assert any("planthopper" in c.text.lower() for c in chunks)
    assert "ICAR" in chunks[0].source


def test_retrieve_respects_k():
    r = Retriever()
    assert len(r.retrieve("crop water soil", k=2)) <= 2


def test_retrieve_gibberish_returns_empty():
    r = Retriever()
    assert r.retrieve("zzz qqqq xxxxx", k=4) == []
