from document_processor import chunk_text, rank_chunks_by_relevance


def test_chunk_text_short_text_single_chunk():
    text = "This is a short document."
    chunks = chunk_text(text, max_words=500, overlap=50)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_splits_long_text():
    text = " ".join(f"word{i}" for i in range(1000))
    chunks = chunk_text(text, max_words=300, overlap=30)
    assert len(chunks) > 1
    # every word should still appear somewhere in the chunks
    all_words = " ".join(chunks).split()
    assert "word0" in all_words
    assert "word999" in all_words


def test_chunk_text_overlap_shares_words():
    text = " ".join(f"word{i}" for i in range(200))
    chunks = chunk_text(text, max_words=100, overlap=20)
    assert len(chunks) >= 2
    tail_of_first = set(chunks[0].split()[-20:])
    head_of_second = set(chunks[1].split()[:20])
    assert tail_of_first & head_of_second


def test_chunk_text_empty_string():
    assert chunk_text("") == []


def test_rank_chunks_prioritizes_relevant_chunk():
    chunks = [
        "The weather today is sunny with a light breeze.",
        "The quarterly revenue grew by twenty percent this year.",
        "Cats are popular pets around the world.",
    ]
    ranked = rank_chunks_by_relevance(chunks, "What was the revenue growth?", top_k=1)
    assert "revenue" in ranked[0].lower()


def test_rank_chunks_falls_back_when_no_overlap():
    chunks = ["Alpha beta gamma.", "Delta epsilon zeta."]
    ranked = rank_chunks_by_relevance(chunks, "unrelated query terms", top_k=2)
    assert len(ranked) == 2
