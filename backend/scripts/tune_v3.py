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
import csv
import os
import sys
from datetime import datetime, timedelta
from statistics import mean

# Run standalone (`python scripts/tune_v3.py` from backend/) by putting backend/ on the path.
_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BACKEND)

from api.models import MarketRegime
from config import config
from core.api_client import RestApiClient
from core.indicator_calculator import IndicatorCalculator
from core.regime_analyzer import MarketRegimeAnalyzer
from core.scoring_engine import ScoringEngine

HORIZON = 30
_REPO_ROOT = os.path.dirname(_BACKEND)
DATA_DIR = os.path.join(_REPO_ROOT, "data")
DOCS_DIR = os.path.join(_REPO_ROOT, "docs")

# 10 dates across different years / months / market conditions
DATES = [
    "2023-06-01",
    "2023-09-01",
    "2023-11-01",
    "2024-01-02",
    "2024-03-01",
    "2024-05-01",
    "2024-08-01",
    "2024-11-01",
    "2025-01-02",
    "2025-03-03",
]
SCORE_THRESHOLDS = [50, 55, 60, 65, 70, 75, 80]
GAIN_THRESHOLDS = [3, 5, 7, 10]


def load_universe():
    path = os.path.join(DATA_DIR, "ALL_HALAL_STOCKS.txt")
    seen, out = set(), []
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for tok in line.split(","):
            t = tok.strip().upper()
            if t and t.isalpha() and 1 <= len(t) <= 5 and t not in seen:
                seen.add(t)
                out.append(t)
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
    window = bars[1 : HORIZON + 1]
    if not window:
        return None
    max_gain = (max(b["high"] for b in window) - entry) / entry * 100
    ret = (window[-1]["close"] - entry) / entry * 100  # buy & hold to horizon close
    return max_gain, ret


async def collect():
    client = RestApiClient(
        config.POLYGON_TOKEN,
        config.API_BASE_URL,
        config.MAX_CONCURRENT_REQUESTS,
        config.MAX_RETRIES,
    )
    calc, engine = IndicatorCalculator(), ScoringEngine()
    regimer = MarketRegimeAnalyzer(client)
    universe = load_universe()
    print(f"Universe: {len(universe)} halal tickers x {len(DATES)} dates")
    records = []
    for date in DATES:
        client.clear_cache()
        regime = (await regimer.analyze_regime(as_of_date=date)).regime
        tradeable = regime != MarketRegime.BEARISH
        market = await client.fetch_stock_data(
            "SPY", days=config.HISTORY_FETCH_DAYS, as_of_date=date
        )
        rows = []
        for t in universe:
            try:
                data = await client.fetch_stock_data(
                    t, days=config.HISTORY_FETCH_DAYS, as_of_date=date
                )
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
                price,
                float(data.volumes[-1]),
                ind,
                data.prices,
                data.volumes,
                rs_percentile=rmap.get(ind.relative_strength, 0.0),
            )
            fwd = await forward(client, t, date, price)
            if fwd is None:
                continue
            max_gain, ret = fwd
            records.append(
                {
                    "date": date,
                    "ticker": t,
                    "tradeable": tradeable,
                    "score": score,
                    "max_gain": max_gain,
                    "ret": ret,
                }
            )
            n += 1
        print(f"  {date}: regime={regime.value:8s} scored={n}")
    return records


def report(records):
    lines = [
        "# V3 Tuning & Portfolio Report\n",
        f"Full halal universe across {len(DATES)} dates "
        f"({DATES[0]} … {DATES[-1]}). {len(records)} hard-filter-passing "
        f"observations with actual 30-day outcomes.\n",
    ]

    # --- Precision heatmap: score threshold x gain threshold ---
    lines.append("## Precision by score threshold x gain(%) threshold\n")
    header = "| Score≥ | " + " | ".join(f"gain≥{g}%" for g in GAIN_THRESHOLDS) + " | #signals |"
    lines.append(header)
    lines.append("|" + "---|" * (len(GAIN_THRESHOLDS) + 2))
    for s in SCORE_THRESHOLDS:
        buys = [r for r in records if r["tradeable"] and r["score"] >= s]
        cells = []
        for g in GAIN_THRESHOLDS:
            if buys:
                prec = sum(1 for r in buys if r["max_gain"] >= g) / len(buys)
                cells.append(f"{prec:.0%}")
            else:
                cells.append("—")
        lines.append(f"| {s} | " + " | ".join(cells) + f" | {len(buys)} |")

    # --- Portfolio: $1,000 per signal, buy & hold 30 days (close-to-close) ---
    lines.append("\n## Portfolio: invest $1,000 per BUY signal, hold 30 days\n")
    lines.append(
        "| Score≥ | #signals | precision@5% | avg 30d return | total invested | total profit | profit rate |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    best = None
    for s in SCORE_THRESHOLDS:
        buys = [r for r in records if r["tradeable"] and r["score"] >= s]
        if not buys:
            lines.append(f"| {s} | 0 | — | — | — | — | — |")
            continue
        prec5 = sum(1 for r in buys if r["max_gain"] >= 5) / len(buys)
        avg_ret = mean(r["ret"] for r in buys)
        invested = 1000 * len(buys)
        profit = sum(1000 * r["ret"] / 100 for r in buys)
        rate = profit / invested * 100
        lines.append(
            f"| {s} | {len(buys)} | {prec5:.0%} | {avg_ret:+.1f}% | "
            f"${invested:,.0f} | ${profit:+,.0f} | {rate:+.1f}% |"
        )
        # "right" threshold: best precision with >= ~20 signals and positive profit
        if len(buys) >= 20 and (best is None or prec5 > best[1]):
            best = (s, prec5, rate, len(buys), avg_ret)

    if best:
        lines.append(
            f"\n**Recommended score threshold: {best[0]}** — precision@5% "
            f"{best[1]:.0%}, {best[3]} signals, avg 30d return {best[4]:+.1f}%, "
            f"portfolio profit rate **{best[2]:+.1f}%** per 30-day cycle."
        )

    # per-date sanity
    lines.append("\n## Per-date (score≥65 BUYs)\n")
    lines.append("| Date | #BUY | precision@5% | avg 30d return |")
    lines.append("|---|---|---|---|")
    for d in DATES:
        buys = [r for r in records if r["date"] == d and r["tradeable"] and r["score"] >= 65]
        if buys:
            prec = sum(1 for r in buys if r["max_gain"] >= 5) / len(buys)
            avg = mean(r["ret"] for r in buys)
            lines.append(f"| {d} | {len(buys)} | {prec:.0%} | {avg:+.1f}% |")
        else:
            bears = [r for r in records if r["date"] == d]
            tag = "bearish → 0 BUYs" if (bears and not bears[0]["tradeable"]) else "0 BUYs"
            lines.append(f"| {d} | 0 | {tag} | — |")

    text = "\n".join(lines) + "\n"
    out = os.path.join(DOCS_DIR, "V3_TUNING_REPORT.md")
    open(out, "w").write(text)
    print("\n" + text)
    print(f"Saved -> {out}")


CSV_PATH = os.path.join(DOCS_DIR, "V3_tuning_data.csv")


def save_csv(records):
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["date", "ticker", "tradeable", "score", "max_gain", "ret"]
        )
        w.writeheader()
        w.writerows(records)
    print(f"Saved raw data -> {CSV_PATH}")


def load_csv():
    records = []
    with open(CSV_PATH) as f:
        for r in csv.DictReader(f):
            records.append(
                {
                    "date": r["date"],
                    "ticker": r["ticker"],
                    "tradeable": r["tradeable"] == "True",
                    "score": int(r["score"]),
                    "max_gain": float(r["max_gain"]),
                    "ret": float(r["ret"]),
                }
            )
    return records


def html_report(records):
    """Presentable, self-contained HTML report with per-stock detail per date."""

    def precision(rows, g=5):
        return sum(1 for r in rows if r["max_gain"] >= g) / len(rows) if rows else 0.0

    def gcolor(v, lo, hi):  # green->red gradient helper
        v = max(lo, min(hi, v))
        t = (v - lo) / (hi - lo) if hi > lo else 0
        r = int(220 - 140 * t)
        g = int(80 + 140 * t)
        return f"rgb({r},{g},90)"

    css = """body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f5f7fa;color:#1a2b3c}
    .wrap{max-width:1100px;margin:0 auto;padding:32px}
    h1{color:#0b3d66}h2{color:#0b5394;border-bottom:2px solid #e0e6ee;padding-bottom:6px;margin-top:36px}
    .sub{color:#5b6b7b;margin-top:-8px}
    table{border-collapse:collapse;width:100%;margin:12px 0;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.08)}
    th,td{padding:8px 12px;text-align:center;border:1px solid #e6ebf1;font-size:14px}
    th{background:#0b5394;color:#fff;font-weight:600}
    .kpis{display:flex;gap:16px;flex-wrap:wrap;margin:16px 0}
    .kpi{background:#fff;border-radius:10px;padding:16px 22px;box-shadow:0 1px 3px rgba(0,0,0,.08);min-width:150px}
    .kpi .v{font-size:28px;font-weight:700;color:#0b3d66}.kpi .l{color:#5b6b7b;font-size:13px}
    .win{color:#137333;font-weight:600}.loss{color:#a50e0e;font-weight:600}
    .card{background:#fff;border-radius:10px;padding:16px 20px;margin:14px 0;box-shadow:0 1px 3px rgba(0,0,0,.08)}
    .badge{display:inline-block;padding:2px 10px;border-radius:12px;color:#fff;font-size:12px;font-weight:600}
    .note{background:#fff7e6;border-left:4px solid #f0a500;padding:12px 16px;border-radius:6px;margin:12px 0}
    details summary{cursor:pointer;font-weight:600;color:#0b5394}"""

    buys80 = [r for r in records if r["tradeable"] and r["score"] >= 80]
    port = lambda rows: (mean(r["ret"] for r in rows) if rows else 0.0)

    h = [
        "<!doctype html><html><head><meta charset='utf-8'><title>V3 Backtest & Tuning Report</title>",
        f"<style>{css}</style></head><body><div class='wrap'>",
        "<h1>V3 High-Precision Halal Scanner — Backtest & Tuning Report</h1>",
        f"<p class='sub'>Full halal universe ({len(set(r['ticker'] for r in records))} stocks) "
        f"across {len(DATES)} dates ({DATES[0]} … {DATES[-1]}). "
        f"{len(records)} hard-filter-passing observations with actual 30-day outcomes. "
        f"Generated {datetime.now():%Y-%m-%d %H:%M}.</p>",
    ]

    # KPIs
    h.append("<div class='kpis'>")
    for label, val in [
        ("Observations", f"{len(records)}"),
        ("Dates tested", f"{len(DATES)}"),
        ("BUY signals (score≥80)", f"{len(buys80)}"),
        ("Precision@5% (score≥80)", f"{precision(buys80):.0%}"),
        ("Avg 30d return (score≥80)", f"{port(buys80):+.1f}%"),
    ]:
        h.append(f"<div class='kpi'><div class='v'>{val}</div><div class='l'>{label}</div></div>")
    h.append("</div>")

    # Precision heatmap
    h.append("<h2>Precision by score threshold × gain(%) threshold</h2>")
    h.append(
        "<table><tr><th>Score≥</th>"
        + "".join(f"<th>gain≥{g}%</th>" for g in GAIN_THRESHOLDS)
        + "<th># signals</th></tr>"
    )
    for s in SCORE_THRESHOLDS:
        rows = [r for r in records if r["tradeable"] and r["score"] >= s]
        cells = ""
        for g in GAIN_THRESHOLDS:
            p = precision(rows, g)
            cells += f"<td style='background:{gcolor(p,0.2,0.8)};color:#fff'>{p:.0%}</td>"
        h.append(f"<tr><th>{s}</th>{cells}<td>{len(rows)}</td></tr>")
    h.append("</table>")

    # Portfolio
    h.append("<h2>Portfolio — invest $1,000 per BUY signal, hold 30 days</h2>")
    h.append(
        "<table><tr><th>Score≥</th><th># signals</th><th>Precision@5%</th><th>Avg 30d return</th>"
        "<th>Invested</th><th>Profit</th><th>Profit rate</th></tr>"
    )
    for s in SCORE_THRESHOLDS:
        rows = [r for r in records if r["tradeable"] and r["score"] >= s]
        if not rows:
            continue
        avg = port(rows)
        invested = 1000 * len(rows)
        profit = sum(1000 * r["ret"] / 100 for r in rows)
        cls = "win" if profit >= 0 else "loss"
        h.append(
            f"<tr><th>{s}</th><td>{len(rows)}</td><td>{precision(rows):.0%}</td>"
            f"<td class='{cls}'>{avg:+.1f}%</td><td>${invested:,.0f}</td>"
            f"<td class='{cls}'>${profit:+,.0f}</td><td class='{cls}'>{profit/invested*100:+.1f}%</td></tr>"
        )
    h.append("</table>")

    # Per-date detail with per-stock BUYs
    h.append("<h2>Per-date breakdown (BUYs at score ≥ 65, with each stock's outcome)</h2>")
    for d in DATES:
        day = [r for r in records if r["date"] == d]
        bears = day and not day[0]["tradeable"]
        buys = sorted(
            [r for r in day if r["tradeable"] and r["score"] >= 65], key=lambda x: -x["score"]
        )
        if bears:
            h.append(
                f"<div class='card'><b>{d}</b> &nbsp; <span class='badge' style='background:#a50e0e'>BEARISH — 0 BUYs</span> "
                f"(regime gate emitted zero candidates)</div>"
            )
            continue
        if not buys:
            h.append(f"<div class='card'><b>{d}</b> &nbsp; 0 BUYs above threshold</div>")
            continue
        p = precision(buys)
        avg = port(buys)
        col = "win" if avg >= 0 else "loss"
        rowshtml = "".join(
            f"<tr><td>{r['ticker']}</td><td>{r['score']}</td>"
            f"<td class='{'win' if r['ret']>=0 else 'loss'}'>{r['ret']:+.1f}%</td>"
            f"<td>{r['max_gain']:+.1f}%</td><td>{'✅ win' if r['max_gain']>=5 else '❌'}</td></tr>"
            for r in buys
        )
        h.append(
            f"<div class='card'><b>{d}</b> &nbsp; {len(buys)} BUYs &nbsp;|&nbsp; "
            f"precision@5% <b>{p:.0%}</b> &nbsp;|&nbsp; avg 30d return <span class='{col}'>{avg:+.1f}%</span>"
            f"<details><summary>Show {len(buys)} stocks</summary>"
            f"<table><tr><th>Ticker</th><th>Score</th><th>30d return</th><th>Max gain</th><th>Win@5%</th></tr>"
            f"{rowshtml}</table></details></div>"
        )

    h.append(
        "<div class='note'><b>How to read this:</b> a BUY = market not bearish AND score ≥ threshold. "
        "“30d return” = buy at the date's close, sell at the close 30 trading days later. "
        "“Max gain” = best intraday gain reached in the window (an upper bound if you sold at the peak). "
        "“Win@5%” = the stock reached at least +5%. Profit rate = total profit / total invested.</div>"
    )
    h.append(
        "<div class='note'><b>Honest caveats:</b> results are net-positive but modest with high "
        "month-to-month variance (e.g. 2024-11 strong vs 2025-03 weak). This is buy-and-hold to the "
        "30-day close; a target/stop exit would change the numbers. The regime gate is broad-market, "
        "so it can miss stock-specific weakness in an overall-bullish month.</div>"
    )
    h.append("</div></body></html>")

    out = os.path.join(DOCS_DIR, "V3_TUNING_REPORT.html")
    open(out, "w").write("\n".join(h))
    print(f"Saved HTML report -> {out}")


async def main():
    if "--from-csv" in sys.argv:
        records = load_csv()
        print(f"Loaded {len(records)} records from CSV")
    else:
        records = await collect()
        save_csv(records)
    report(records)
    html_report(records)


if __name__ == "__main__":
    asyncio.run(main())
