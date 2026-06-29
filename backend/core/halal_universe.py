"""Halal stock universe loader.

Parses the curated halal ticker list at ``data/ALL_HALAL_STOCKS.txt`` (a comma-separated
file with ``#`` comments) into a deduplicated, ordered list of symbols. Cached so the file
is read only once per process.
"""

import os
from functools import lru_cache

_DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "ALL_HALAL_STOCKS.txt",
)


@lru_cache(maxsize=1)
def load_halal_universe() -> tuple[str, ...]:
    """Return the full halal universe as a deduplicated tuple of ticker symbols.

    Returns:
        Ordered tuple of unique uppercase tickers parsed from the data file.
        Empty tuple if the file is missing.
    """
    if not os.path.exists(_DATA_FILE):
        return ()

    seen: set[str] = set()
    out: list[str] = []
    with open(_DATA_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            for token in line.split(","):
                ticker = token.strip().upper()
                if ticker and ticker.isalpha() and 1 <= len(ticker) <= 5 and ticker not in seen:
                    seen.add(ticker)
                    out.append(ticker)
    return tuple(out)
