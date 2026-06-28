"""
V3 comprehensive tuning + portfolio simulation (spec task 4.6).

Full halal universe x 10 dates across different years/months/periods. For every
hard-filter-passing ticker it records score + regime + the actual 30-day outcome
(max gain AND realized close-to-close return), then:

  1. Sweeps SCORE threshold x GAIN(%) threshold -> precision per cell.
  2. Per score threshold: #signals, precision@5%, avg 30d return,
     and a $1,000-per-signal portfolio profit rate.

Run: python tune_v3.py            (writes V3_TUNING_REPORT.md)
"""
import asyncio
import os
from datetime import datetime, timedelta
from statistics import mean

from core.api_client import RestApiClient
from core.indicator_calculator import IndicatorCalculator
from core.scoring_engine import ScoringEngine
from api.models import MarketRegime
from core.regime_analyzer import MarketRegimeAnalyzer
from config import config

HORIZON = 30
HERE = os.path.dirname(__file__)

# 10 dates across different years / months / market conditions
DATES = [
    '2023-06-01', '2023-09-01', '2023-11-01',
    '2024-01-02', '2024-03-01', '2024-05-01', '2024-08-01', '2024-11-01',
    '2025-01-02', '2025-03-03',
]
SCORE_THRESHOLDS = [50, 55, 60, 65, 70, 75, 80]
GAIN_THRESHOLDS = [3, 5, 7, 10]


def load_universe():
    path = os.path.join(HERE, '..', 'ALL_HALAL_STOCKS.txt')
    seen, out = set(), []
    for line in open(path):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        for tok in line.split(','):
            t = tok.strip().upper()
            if t and t.isalpha() and 1 <= len(t) <= 5 and t not in seen:
                seen.add(t); out.append(t)
    return out


async def forward(client, ticker, as_of_date, entry):
    start = datetime.strptime(as_of_date, "%Y-%m-%d")
    end = start + timedelta(days=int(HORIZON * 1.7))
    try:
        bars = await client.fetch_stock_data_range(ticker, as_of_date, end.strftime("%Y-%m-%d"))
    except Exception:
        return None
    if not bars or len(bars) < 2:
        return None
    window = bars[1:HORIZON + 1]
    if not window:
        return None
    max_gain = (max(b["high"] for b in window) - entry) / entry * 100
    ret = (window[-1]["close"] - entry) / entry * 100  # buy & hold to horizon close
    return max_gain, ret


async def collect():
    client = RestApiClient(config.POLYGON_TOKEN, config.API_BASE_URL,
                           config.MAX_CONCURRENT_REQUESTS, config.MAX_RETRIES)
    calc, engine = IndicatorCalculator(), ScoringEngine()
    regimer = MarketRegimeAnalyzer(client)
    universe = load_universe()
    print(f"Universe: {len(universe)} halal tickers x {len(DATES)} dates")
    records = []
    for date in DATES:
        client.clear_cache()
        regime = (await regimer.analyze_regime(as_of_date=date)).regime
        tradeable = regime != MarketRegime.BEARISH
        market = await client.fetch_stock_data("SPY", days=config.HISTORY_FETCH_DAYS, as_of_date=date)
        rows = []
        for t in universe:
            try:
                data = await client.fetch_stock_data(t, days=config.HISTORY_FETCH_DAYS, as_of_date=date)
                ind = calc.calculate_all(data, market)
                rows.append((t, data, ind))
            except Exception:
                continue
        rs_vals = sorted(r[2].relative_strength for r in rows if r[2].relative_strength is not None)
        rmap = {v: i / len(rs_vals) * 100 for i, v in enumerate(rs_vals)} if rs_vals else {}
        n = 0
        for t, data, ind in rows:
            price = float(data.prices[-1])
            ok, _ = engine.passes_hard_filters(price, ind)
            if not ok:
                continue
            score, *_ = engine.calculate_enhanced_score(
                price, float(data.volumes[-1]), ind, data.prices, data.volumes,
                rs_percentile=rmap.get(ind.relative_strength, 0.0))
            fwd = await forward(client, t, date, price)
            if fwd is None:
                continue
            max_gain, ret = fwd
            records.append({'date': date, 'ticker': t, 'tradeable': tradeable,
                            'score': score, 'max_gain': max_gain, 'ret': ret})
            n += 1
        print(f"  {date}: regime={regime.value:8s} scored={n}")
    return records


def report(records):
    lines = ["# V3 Tuning & Portfolio Report\n",
             f"Full halal universe across {len(DATES)} dates "
             f"({DATES[0]} … {DATES[-1]}). {len(records)} hard-filter-passing "
             f"observations with actual 30-day outcomes.\n"]

    # --- Precision heatmap: score threshold x gain threshold ---
    lines.append("## Precision by score threshold x gain(%) threshold\n")
    header = "| Score≥ | " + " | ".join(f"gain≥{g}%" for g in GAIN_THRESHOLDS) + " | #signals |"
    lines.append(header)
    lines.append("|" + "---|" * (len(GAIN_THRESHOLDS) + 2))
    for s in SCORE_THRESHOLDS:
        buys = [r for r in records if r['tradeable'] and r['score'] >= s]
        cells = []
        for g in GAIN_THRESHOLDS:
            if buys:
                prec = sum(1 for r in buys if r['max_gain'] >= g) / len(buys)
                cells.append(f"{prec:.0%}")
            else:
                cells.append("—")
        lines.append(f"| {s} | " + " | ".join(cells) + f" | {len(buys)} |")

    # --- Portfolio: $1,000 per signal, buy & hold 30 days (close-to-close) ---
    lines.append("\n## Portfolio: invest $1,000 per BUY signal, hold 30 days\n")
    lines.append("| Score≥ | #signals | precision@5% | avg 30d return | total invested | total profit | profit rate |")
    lines.append("|---|---|---|---|---|---|---|")
    best = None
    for s in SCORE_THRESHOLDS:
        buys = [r for r in records if r['tradeable'] and r['score'] >= s]
        if not buys:
            lines.append(f"| {s} | 0 | — | — | — | — | — |")
            continue
        prec5 = sum(1 for r in buys if r['max_gain'] >= 5) / len(buys)
        avg_ret = mean(r['ret'] for r in buys)
        invested = 1000 * len(buys)
        profit = sum(1000 * r['ret'] / 100 for r in buys)
        rate = profit / invested * 100
        lines.append(f"| {s} | {len(buys)} | {prec5:.0%} | {avg_ret:+.1f}% | "
                     f"${invested:,.0f} | ${profit:+,.0f} | {rate:+.1f}% |")
        # "right" threshold: best precision with >= ~20 signals and positive profit
        if len(buys) >= 20 and (best is None or prec5 > best[1]):
            best = (s, prec5, rate, len(buys), avg_ret)

    if best:
        lines.append(f"\n**Recommended score threshold: {best[0]}** — precision@5% "
                     f"{best[1]:.0%}, {best[3]} signals, avg 30d return {best[4]:+.1f}%, "
                     f"portfolio profit rate **{best[2]:+.1f}%** per 30-day cycle.")

    # per-date sanity
    lines.append("\n## Per-date (score≥65 BUYs)\n")
    lines.append("| Date | #BUY | precision@5% | avg 30d return |")
    lines.append("|---|---|---|---|")
    for d in DATES:
        buys = [r for r in records if r['date'] == d and r['tradeable'] and r['score'] >= 65]
        if buys:
            prec = sum(1 for r in buys if r['max_gain'] >= 5) / len(buys)
            avg = mean(r['ret'] for r in buys)
            lines.append(f"| {d} | {len(buys)} | {prec:.0%} | {avg:+.1f}% |")
        else:
            bears = [r for r in records if r['date'] == d]
            tag = "bearish → 0 BUYs" if (bears and not bears[0]['tradeable']) else "0 BUYs"
            lines.append(f"| {d} | 0 | {tag} | — |")

    text = "\n".join(lines) + "\n"
    out = os.path.join(HERE, '..', 'V3_TUNING_REPORT.md')
    open(out, 'w').write(text)
    print("\n" + text)
    print(f"Saved -> {out}")


async def main():
    report(await collect())


if __name__ == '__main__':
    asyncio.run(main())
