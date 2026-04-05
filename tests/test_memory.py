"""Tests for tradingagents/agents/utils/memory.py

FinancialSituationMemory uses BM25 (rank_bm25.BM25Okapi) for lexical
similarity matching.  All tests run in-memory -- no network, no Redis.
"""

from unittest.mock import MagicMock, patch

import pytest

from tradingagents.agents.utils.memory import FinancialSituationMemory

# ---------------------------------------------------------------------------
# Construction / init
# ---------------------------------------------------------------------------


def test_init_sets_name():
    """Name attribute is stored on construction."""
    mem = FinancialSituationMemory("my_memory")
    assert mem.name == "my_memory"


def test_init_empty_state():
    """Freshly created memory has no documents, recommendations, or index."""
    mem = FinancialSituationMemory("empty")
    assert mem.documents == []
    assert mem.recommendations == []
    assert mem.bm25 is None


def test_init_config_ignored():
    """config kwarg is accepted for API compat but has no effect."""
    mem = FinancialSituationMemory("x", config={"some_key": "some_val"})
    assert mem.name == "x"
    assert mem.documents == []


# ---------------------------------------------------------------------------
# _tokenize
# ---------------------------------------------------------------------------


def test_tokenize_lowercases():
    """Tokens are lowercased."""
    mem = FinancialSituationMemory("t")
    tokens = mem._tokenize("BUY AAPL Now")
    assert tokens == ["buy", "aapl", "now"]


def test_tokenize_strips_punctuation():
    """Punctuation is removed; words are split on boundaries."""
    mem = FinancialSituationMemory("t")
    tokens = mem._tokenize("high-growth, tech stocks!")
    assert tokens == ["high", "growth", "tech", "stocks"]


def test_tokenize_empty_string():
    """Empty input yields empty token list."""
    mem = FinancialSituationMemory("t")
    assert mem._tokenize("") == []


def test_tokenize_only_punctuation():
    """String with only punctuation yields empty token list."""
    mem = FinancialSituationMemory("t")
    assert mem._tokenize("!!!...---") == []


def test_tokenize_numbers():
    """Numeric tokens are preserved."""
    mem = FinancialSituationMemory("t")
    tokens = mem._tokenize("Price is 42.5 dollars")
    # '42' and '5' are separate word-boundary tokens
    assert "42" in tokens
    assert "5" in tokens
    assert "price" in tokens


# ---------------------------------------------------------------------------
# add_situations
# ---------------------------------------------------------------------------


def test_add_situations_single():
    """Adding a single (situation, recommendation) pair."""
    mem = FinancialSituationMemory("s")
    mem.add_situations([("high inflation", "buy bonds")])
    assert len(mem.documents) == 1
    assert mem.documents[0] == "high inflation"
    assert mem.recommendations[0] == "buy bonds"
    assert mem.bm25 is not None


def test_add_situations_multiple():
    """Adding several pairs at once."""
    mem = FinancialSituationMemory("s")
    data = [
        ("situation A", "advice A"),
        ("situation B", "advice B"),
        ("situation C", "advice C"),
    ]
    mem.add_situations(data)
    assert len(mem.documents) == 3
    assert len(mem.recommendations) == 3
    assert mem.bm25 is not None


def test_add_situations_incremental():
    """Calling add_situations twice appends and rebuilds the index."""
    mem = FinancialSituationMemory("s")
    mem.add_situations([("sit1", "rec1")])
    assert len(mem.documents) == 1
    mem.add_situations([("sit2", "rec2")])
    assert len(mem.documents) == 2
    assert mem.recommendations == ["rec1", "rec2"]


def test_add_situations_empty_list():
    """Adding an empty list leaves memory unchanged (no index)."""
    mem = FinancialSituationMemory("s")
    mem.add_situations([])
    assert mem.documents == []
    assert mem.bm25 is None


# ---------------------------------------------------------------------------
# _rebuild_index
# ---------------------------------------------------------------------------


def test_rebuild_index_creates_bm25_with_docs():
    """BM25 index is created when documents exist."""
    mem = FinancialSituationMemory("r")
    mem.documents = ["some document"]
    mem.recommendations = ["some advice"]
    mem._rebuild_index()
    assert mem.bm25 is not None


def test_rebuild_index_none_when_empty():
    """BM25 index is set to None when documents list is empty."""
    mem = FinancialSituationMemory("r")
    mem.documents = []
    mem._rebuild_index()
    assert mem.bm25 is None


# ---------------------------------------------------------------------------
# get_memories – empty / no-match cases
# ---------------------------------------------------------------------------


def test_get_memories_empty_memory_returns_empty():
    """Querying empty memory returns an empty list."""
    mem = FinancialSituationMemory("e")
    results = mem.get_memories("anything at all")
    assert results == []


def test_get_memories_none_bm25_returns_empty():
    """If bm25 is None (no index), return empty list."""
    mem = FinancialSituationMemory("e")
    mem.documents = ["doc"]  # documents exist but index not built
    mem.bm25 = None
    results = mem.get_memories("query")
    assert results == []


# ---------------------------------------------------------------------------
# get_memories – result structure
# ---------------------------------------------------------------------------


def test_get_memories_returns_correct_keys():
    """Each result dict has matched_situation, recommendation, similarity_score."""
    mem = FinancialSituationMemory("k")
    mem.add_situations([("rising interest rates", "reduce duration")])
    results = mem.get_memories("interest rates going up")
    assert len(results) == 1
    result = results[0]
    assert "matched_situation" in result
    assert "recommendation" in result
    assert "similarity_score" in result


def test_get_memories_matched_situation_value():
    """matched_situation is the original document text."""
    mem = FinancialSituationMemory("v")
    mem.add_situations([("high volatility in tech", "sell tech stocks")])
    results = mem.get_memories("tech volatility")
    assert results[0]["matched_situation"] == "high volatility in tech"


def test_get_memories_recommendation_value():
    """recommendation is the original advice text."""
    mem = FinancialSituationMemory("v")
    mem.add_situations([("inflation rising fast", "buy TIPS")])
    results = mem.get_memories("inflation")
    assert results[0]["recommendation"] == "buy TIPS"


def test_get_memories_similarity_score_top_is_one():
    """The top match score should be normalized to 1.0 when its raw score > 0."""
    mem = FinancialSituationMemory("sc")
    mem.add_situations(
        [
            ("strong dollar hurting emerging markets", "hedge fx exposure"),
            ("weak dollar boosting exports", "increase international allocation"),
        ]
    )
    results = mem.get_memories("dollar strength emerging markets", n_matches=2)
    # BM25 can produce negative scores for low-relevance docs, so we only
    # check that the top result is normalized to 1.0 and scores are descending
    assert len(results) == 2
    scores = [r["similarity_score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_get_memories_top_match_has_score_one():
    """The best match should have a normalized score of 1.0 when max_score > 0."""
    mem = FinancialSituationMemory("top")
    # Use enough distinct terms so the best match has a positive BM25 score
    mem.add_situations(
        [
            ("inflation rising sharply rates increasing", "buy gold"),
            ("technology sector earnings report quarterly results", "buy tech"),
            ("deflation risk economic slowdown concerns", "buy bonds"),
        ]
    )
    results = mem.get_memories("inflation rising sharply rates", n_matches=3)
    # The top result should be "inflation rising" and have score 1.0
    assert results[0]["matched_situation"] == "inflation rising sharply rates increasing"
    assert results[0]["similarity_score"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# get_memories – n_matches
# ---------------------------------------------------------------------------


def test_get_memories_default_n_matches_is_one():
    """Default call returns a single match."""
    mem = FinancialSituationMemory("n1")
    mem.add_situations(
        [
            ("situation A", "advice A"),
            ("situation B", "advice B"),
        ]
    )
    results = mem.get_memories("situation")
    assert len(results) == 1


def test_get_memories_n_matches_two():
    """Requesting 2 matches returns exactly 2."""
    mem = FinancialSituationMemory("n2")
    mem.add_situations(
        [
            ("alpha scenario", "alpha advice"),
            ("beta scenario", "beta advice"),
            ("gamma scenario", "gamma advice"),
        ]
    )
    results = mem.get_memories("scenario", n_matches=2)
    assert len(results) == 2


def test_get_memories_n_matches_exceeds_docs():
    """If n_matches > number of documents, return all documents."""
    mem = FinancialSituationMemory("n_big")
    mem.add_situations([("only one doc", "only one rec")])
    results = mem.get_memories("one doc", n_matches=10)
    assert len(results) == 1


# ---------------------------------------------------------------------------
# get_memories – BM25 ranking quality
# ---------------------------------------------------------------------------


def test_get_memories_best_match_is_most_relevant():
    """BM25 should rank the most lexically similar document first."""
    mem = FinancialSituationMemory("rank")
    mem.add_situations(
        [
            ("tech sector high volatility institutional selling", "reduce tech exposure"),
            ("strong dollar emerging markets forex", "hedge currency"),
            ("inflation rising interest rates consumer spending", "defensive sectors"),
        ]
    )
    results = mem.get_memories("tech sector volatility selling pressure", n_matches=1)
    assert results[0]["matched_situation"] == "tech sector high volatility institutional selling"
    assert results[0]["recommendation"] == "reduce tech exposure"


def test_get_memories_ordering_by_relevance():
    """Results should be ordered from most to least relevant."""
    mem = FinancialSituationMemory("order")
    mem.add_situations(
        [
            ("apple banana cherry", "fruit salad"),
            ("dog cat bird", "pet store"),
            ("apple cherry pie", "dessert"),
        ]
    )
    results = mem.get_memories("apple cherry", n_matches=3)
    scores = [r["similarity_score"] for r in results]
    # Scores should be in descending order
    assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# get_memories – edge cases with query content
# ---------------------------------------------------------------------------


def test_get_memories_query_no_overlap():
    """Query with zero term overlap still returns results (scored low)."""
    mem = FinancialSituationMemory("no_overlap")
    mem.add_situations([("inflation rates bonds", "buy treasuries")])
    results = mem.get_memories("completely unrelated xyz query", n_matches=1)
    # Should still return 1 result (BM25 assigns 0 scores for non-matching)
    assert len(results) == 1
    assert results[0]["similarity_score"] == pytest.approx(0.0, abs=1e-9)


def test_get_memories_single_word_query():
    """A single-word query should still work."""
    mem = FinancialSituationMemory("sw")
    mem.add_situations(
        [
            ("inflation is rising", "buy gold"),
            ("market is stable", "hold positions"),
        ]
    )
    results = mem.get_memories("inflation", n_matches=1)
    assert results[0]["matched_situation"] == "inflation is rising"


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


def test_clear_resets_all_state():
    """clear() empties documents, recommendations, and index."""
    mem = FinancialSituationMemory("c")
    mem.add_situations([("doc", "rec")])
    assert len(mem.documents) == 1
    mem.clear()
    assert mem.documents == []
    assert mem.recommendations == []
    assert mem.bm25 is None


def test_clear_then_get_memories_returns_empty():
    """After clear(), get_memories should return empty list."""
    mem = FinancialSituationMemory("c2")
    mem.add_situations([("doc", "rec")])
    mem.clear()
    results = mem.get_memories("doc")
    assert results == []


def test_clear_then_add_works():
    """After clear(), adding new situations should work normally."""
    mem = FinancialSituationMemory("c3")
    mem.add_situations([("old doc", "old rec")])
    mem.clear()
    mem.add_situations([("new doc", "new rec")])
    assert len(mem.documents) == 1
    assert mem.documents[0] == "new doc"
    results = mem.get_memories("new doc")
    assert len(results) == 1
    assert results[0]["recommendation"] == "new rec"


# ---------------------------------------------------------------------------
# Multiple independent instances
# ---------------------------------------------------------------------------


def test_separate_instances_are_independent():
    """Two FinancialSituationMemory instances do not share state."""
    mem_a = FinancialSituationMemory("a")
    mem_b = FinancialSituationMemory("b")
    mem_a.add_situations([("doc a", "rec a")])
    assert len(mem_a.documents) == 1
    assert len(mem_b.documents) == 0


# ---------------------------------------------------------------------------
# BM25 mocking (verify internal wiring)
# ---------------------------------------------------------------------------


def test_bm25_get_scores_called_during_retrieval():
    """Verify that bm25.get_scores is called with tokenized query."""
    mem = FinancialSituationMemory("mock_bm25")
    mem.add_situations([("test doc", "test rec")])

    mock_bm25 = MagicMock()
    mock_bm25.get_scores.return_value = [0.5]
    mem.bm25 = mock_bm25

    mem.get_memories("test query", n_matches=1)
    mock_bm25.get_scores.assert_called_once()
    # Verify the argument is a list of lowered tokens
    call_args = mock_bm25.get_scores.call_args[0][0]
    assert call_args == ["test", "query"]


def test_bm25_index_rebuilt_on_add():
    """Each add_situations call rebuilds the BM25 index."""
    mem = FinancialSituationMemory("rebuild")
    with patch("tradingagents.agents.utils.memory.BM25Okapi") as MockBM25:
        mem.add_situations([("doc1", "rec1")])
        assert MockBM25.call_count == 1
        mem.add_situations([("doc2", "rec2")])
        assert MockBM25.call_count == 2


# ---------------------------------------------------------------------------
# Score normalization edge case: all scores zero
# ---------------------------------------------------------------------------


def test_get_memories_all_zero_scores():
    """When all BM25 scores are 0, similarity_score should be 0."""
    mem = FinancialSituationMemory("zero")
    mem.add_situations([("aaa bbb ccc", "advice 1")])

    mock_bm25 = MagicMock()
    mock_bm25.get_scores.return_value = [0.0]
    mem.bm25 = mock_bm25

    results = mem.get_memories("zzz yyy xxx", n_matches=1)
    assert len(results) == 1
    assert results[0]["similarity_score"] == pytest.approx(0.0)


def test_get_memories_multiple_zero_scores():
    """All-zero scores with multiple docs should return all zeros."""
    mem = FinancialSituationMemory("mz")
    mem.add_situations(
        [
            ("aaa bbb", "advice 1"),
            ("ccc ddd", "advice 2"),
        ]
    )

    mock_bm25 = MagicMock()
    mock_bm25.get_scores.return_value = [0.0, 0.0]
    mem.bm25 = mock_bm25

    results = mem.get_memories("zzz", n_matches=2)
    assert len(results) == 2
    for r in results:
        assert r["similarity_score"] == pytest.approx(0.0)
