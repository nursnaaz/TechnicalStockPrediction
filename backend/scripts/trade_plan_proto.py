"""
PROTOTYPE: equity trade-plan engine + backtest (no options trading — options data, if
any, is only a volatility input). For each ticker on a historical as-of date it builds:

    entry, stop (1.5*ATR, capped -8%), target1 (2R), target2 (3R), expected 30d move,
    nearest resistance, reward:risk

then walks the next 30 trading days bar-by-bar to see what actually happened (did target
or stop hit first?), and aggregates hit-rate / expectancy so we can judge if it works.

Run from backend/:  python scripts/trade_plan_proto.py
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from statistics import mean, pstdev

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config  # noqa: E402
from core.api_client import RestApiClient  # noqa: E402

HORIZON = 30  # trading days forward
ATR_N = 14
SIGMA_N = 20

# Diversified, liquid halal names
TICKERS = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AVGO", "LLY", "UNH", "COST", "HD", "CRM",
    "AMD", "QCOM", "TXN", "CAT", "DE", "XOM", "CVX", "V", "MA", "TSM",
]
DATES = ["2024-08-01", "2024-11-01", "2025-01-02"]


def atr(highs, lows, closes, n=ATR_N):
    trs = []
    for i in range(1, len(highs)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    return mean(trs[-n:]) if len(trs) >= n else (mean(trs) if trs else 0.0)


def build_plan(bars):
    highs = [b["high"] for b in bars]
    lows = [b["low"] for b in bars]
    closes = [b["close"] for b in bars]
    entry = closes[-1]
    a = atr(highs, lows, closes)
    rets = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]
    sigma = pstdev(rets[-SIGMA_N:]) if len(rets) >= SIGMA_N else (pstdev(rets) if len(rets) > 1 else 0)
    exp_move = entry * sigma * (HORIZON**0.5)  # 1-sigma 30-day move ($)

    stop = max(entry - 1.5 * a, entry * 0.92)  # 1.5 ATR, capped at -8%
    risk = entry - stop
    if risk <= 0:
        return None
    t1 = entry + 2.0 * risk  # 2R
    t2 = entry + 3.0 * risk  # 3R
    resistance = max(highs[-60:]) if len(highs) >= 60 else max(highs)
    return {
        "entry": entry, "stop": stop, "t1": t1, "t2": t2, "risk": risk,
        "exp_move_pct": exp_move / entry * 100, "atr_pct": a / entry * 100,
        "t1_pct": (t1 - entry) / entry * 100, "stop_pct": (stop - entry) / entry * 100,
        "resistance_pct": (resistance - entry) / entry * 100,
    }


def evaluate(plan, fwd):
    """Walk forward bars; record which of stop / t1 / t2 is hit first (path-dependent)."""
    hit_t1 = hit_t2 = hit_stop = False
    first = "open"  # what resolved first
    for b in fwd[:HORIZON]:
        if not hit_stop and not hit_t1 and b["low"] <= plan["stop"]:
            hit_stop = True
            first = "stop" if first == "open" else first
            break  # stopped out — trade over
        if b["high"] >= plan["t1"]:
            hit_t1 = True
            if first == "open":
                first = "t1"
        if b["high"] >= plan["t2"]:
            hit_t2 = True
    final = fwd[min(HORIZON, len(fwd)) - 1]["close"] if fwd else plan["entry"]
    realized_R = (final - plan["entry"]) / plan["risk"]
    return {"hit_t1": hit_t1, "hit_t2": hit_t2, "hit_stop": hit_stop, "first": first,
            "realized_R": realized_R}


async def main():
    client = RestApiClient(config.POLYGON_TOKEN, config.API_BASE_URL,
                           config.MAX_CONCURRENT_REQUESTS, config.MAX_RETRIES)
    rows = []
    for date in DATES:
        d = datetime.strptime(date, "%Y-%m-%d")
        hist_from = (d - timedelta(days=150)).strftime("%Y-%m-%d")
        fwd_to = (d + timedelta(days=int(HORIZON * 1.7))).strftime("%Y-%m-%d")
        for t in TICKERS:
            try:
                hist = await client.fetch_stock_data_range(t, hist_from, date)
                fwd = await client.fetch_stock_data_range(t, date, fwd_to)
            except Exception:
                continue
            if len(hist) < 60 or len(fwd) < 5:
                continue
            # only "in an uptrend" names (price > 50-day SMA), our real use-case proxy
            sma50 = mean([b["close"] for b in hist][-50:])
            if hist[-1]["close"] <= sma50:
                continue
            plan = build_plan(hist)
            if not plan:
                continue
            res = evaluate(plan, fwd[1:])  # skip entry-day bar
            rows.append({"date": date, "ticker": t, **plan, **res})

    if not rows:
        print("no rows")
        return

    n = len(rows)
    t1_rate = sum(r["hit_t1"] for r in rows) / n
    t2_rate = sum(r["hit_t2"] for r in rows) / n
    stop_rate = sum(r["hit_stop"] for r in rows) / n
    first_t1 = sum(1 for r in rows if r["first"] == "t1") / n  # target before stop
    first_stop = sum(1 for r in rows if r["first"] == "stop") / n
    avg_R = mean(r["realized_R"] for r in rows)
    # expectancy of the 2R-target / 1R-stop rule (path-dependent first-touch)
    exp_2R = first_t1 * 2.0 - first_stop * 1.0

    print(f"\nSAMPLE: {n} uptrend trade-plans across {len(DATES)} dates")
    print(f"  avg ATR move/30d (1-sigma): {mean(r['exp_move_pct'] for r in rows):+.1f}%")
    print(f"  avg target1 (+2R): {mean(r['t1_pct'] for r in rows):+.1f}% | "
          f"avg stop: {mean(r['stop_pct'] for r in rows):+.1f}%")
    print(f"\n  Target1 (2R) ever reached in 30d : {t1_rate:.0%}")
    print(f"  Target2 (3R) ever reached        : {t2_rate:.0%}")
    print(f"  Stop ever hit                    : {stop_rate:.0%}")
    print(f"\n  FIRST-TOUCH (path-dependent, the real test):")
    print(f"    target1 before stop            : {first_t1:.0%}")
    print(f"    stopped out first              : {first_stop:.0%}")
    print(f"    neither (ran 30d)              : {1-first_t1-first_stop:.0%}")
    print(f"\n  Expectancy of 2R/1R rule         : {exp_2R:+.2f}R per trade")
    print(f"  Avg realized R (buy & hold 30d)  : {avg_R:+.2f}R")


if __name__ == "__main__":
    asyncio.run(main())
