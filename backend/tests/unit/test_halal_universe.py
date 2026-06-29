"""Tests for the halal universe loader."""

from core.halal_universe import load_halal_universe


def test_loads_nonempty_deduped_universe():
    universe = load_halal_universe()
    assert len(universe) > 100  # full list is ~212
    assert len(universe) == len(set(universe))  # deduplicated
    assert all(t.isalpha() and t.isupper() for t in universe)


def test_includes_known_halal_tickers():
    universe = set(load_halal_universe())
    for t in ("AAPL", "MSFT", "NVDA", "LLY", "XOM"):
        assert t in universe
