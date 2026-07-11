import pytest

from search_engine import search_folder


def test_search_finds_matches_across_files(nested_folder):
    df = search_folder(".", "Phoenix", recursive=True)
    assert len(df) == 2
    assert set(df["file"]) == {"top.txt", "sub/inner.txt"}


def test_search_is_case_insensitive(nested_folder):
    df = search_folder(".", "phoenix", recursive=True)
    assert len(df) == 2


def test_search_no_matches_returns_empty(nested_folder):
    df = search_folder(".", "nonexistent_keyword_xyz", recursive=True)
    assert df.empty


def test_search_respects_non_recursive(nested_folder):
    df = search_folder(".", "Phoenix", recursive=False)
    assert list(df["file"]) == ["top.txt"]


def test_search_empty_keyword_raises(nested_folder):
    with pytest.raises(ValueError):
        search_folder(".", "   ")


def test_search_snippets_contain_context(sample_txt):
    df = search_folder(".", "budget", recursive=True)
    assert len(df) == 1
    snippet = df.iloc[0]["snippets"][0]
    assert "budget" in snippet.lower()
