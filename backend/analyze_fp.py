"""
False-positive research (spec task: improve V3 precision).

For each ticker on a set of dates: fetch point-in-time history, compute the FULL
indicator set + score, then fetch forward data to learn the actual 30-day max gain.
Classify each BUY (score >= threshold) as TP (gain>=5%) or FP (gain<5%) and compare
the indicator profiles of FPs vs TPs to find what discriminates them.

Usage: python analyze_fp.py [date ...]   (defaults to the weak in-sample dates)
"""
import asyncio
import sys
from statistics import mean, median

from config import config
from core.api_client import RestApiClient
from core.indicator_calculator import IndicatorCalculator
from core.scoring_engine import ScoringEngine

DATES = sys.argv[1:] or ["2025-02-01", "2024-08-01", "2024-03-01", "2024-07-01"]
THRESHOLD = 65
HORIZON = 30

UNIVERSE = [
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "GOOG",
    "TSLA",
    "AVGO",
    "LLY",
    "JNJ",
    "UNH",
    "PFE",
    "ABBV",
    "TMO",
    "ABT",
    "DHR",
    "MRK",
    "BMY",
    "AMGN",
    "GILD",
    "REGN",
    "VRTX",
    "ISRG",
    "HD",
    "COST",
    "TGT",
    "NKE",
    "SBUX",
    "MCD",
    "CMG",
    "LULU",
    "PG",
    "KO",
    "PEP",
    "WMT",
    "ORCL",
    "ADBE",
    "CRM",
    "CSCO",
    "INTC",
    "AMD",
    "QCOM",
    "TXN",
    "AMAT",
    "LRCX",
    "KLAC",
    "MRVL",
    "BA",
    "CAT",
    "DE",
    "UPS",
    "HON",
    "GE",
    "LMT",
    "RTX",
    "XOM",
    "CVX",
    "COP",
    "SLB",
    "EOG",
    "LIN",
    "APD",
    "SHW",
    "T",
    "VZ",
    "TMUS",
    "V",
    "MA",
    "PYPL",
    "SHOP",
    "UBER",
    "DDOG",
    "CRWD",
    "ZS",
    "PANW",
    "NET",
    "MDB",
    "SNOW",
    "NOW",
    "TSM",
    "IBM",
    "CL",
    "KMB",
    "HSY",
    "MDLZ",
    "BKNG",
    "PLD",
    "AMT",
    "EQIX",
    "PSA",
    "DLR",
    "BBY",
    "SNPS",
    "CDNS",
    "NXPI",
    "ADI",
    "AMZN",
    "META",
    "ENPH",
    "FSLR",
]


def features(price, ind, rs_pct):
    dist_sma50 = ((price - ind.sma_50) / ind.sma_50 * 100) if ind.sma_50 else None
    dist_sma200 = ((price - ind.sma_200) / ind.sma_200 * 100) if ind.sma_200 else None
    return {
        "score": None,
        "rsi": ind.rsi_14,
        "roc": ind.roc_10,
        "rs_raw": ind.relative_strength,
        "rs_pct": rs_pct,
        "prox20d": ind.proximity_to_20d_high,
        "dist_sma50": dist_sma50,
        "dist_sma200": dist_sma200,
        "macd_diff": (ind.macd_line - ind.macd_signal)
        if (ind.macd_line is not None and ind.macd_signal is not None)
        else None,
    }


async def fwd_max_gain(client, ticker, as_of_date, entry):
    from datetime import datetime, timedelta

    start = datetime.strptime(as_of_date, "%Y-%m-%d")
    end = start + timedelta(days=int(HORIZON * 1.6))
    try:
        bars = await client.fetch_stock_data_range(ticker, as_of_date, end.strftime("%Y-%m-%d"))
    except Exception:
        return None
    if not bars or len(bars) < 2:
        return None
    window = bars[1 : HORIZON + 1]  # forward bars after the entry day
    if not window:
        return None
    return (max(b["high"] for b in window) - entry) / entry * 100


async def main():
    client = RestApiClient(
        config.POLYGON_TOKEN,
        config.API_BASE_URL,
        config.MAX_CONCURRENT_REQUESTS,
        config.MAX_RETRIES,
    )
    calc = IndicatorCalculator()
    engine = ScoringEngine()
    tps, fps = [], []

    for date in DATES:
        client.clear_cache()
        market = await client.fetch_stock_data(
            "SPY", days=config.HISTORY_FETCH_DAYS, as_of_date=date
        )
        rows = []
        for t in UNIVERSE:
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

        for t, data, ind in rows:
            price = float(data.prices[-1])
            ok, _ = engine.passes_hard_filters(price, ind)
            if not ok:
                continue
            rs_pct = rmap.get(ind.relative_strength, 0.0)
            score, _s, _st, _pt = engine.calculate_enhanced_score(
                price, float(data.volumes[-1]), ind, data.prices, data.volumes, rs_percentile=rs_pct
            )
            if score < THRESHOLD:
                continue
            gain = await fwd_max_gain(client, t, date, price)
            if gain is None:
                continue
            f = features(price, ind, rs_pct)
            f["score"] = score
            f["ticker"] = t
            f["date"] = date
            f["gain"] = gain
            (tps if gain >= 5 else fps).append(f)

    print(
        f"\nBUYs: {len(tps)+len(fps)}  TP={len(tps)}  FP={len(fps)}  "
        f"precision={len(tps)/(len(tps)+len(fps)):.1%}"
        if (tps or fps)
        else "no BUYs"
    )

    keys = ["score", "rsi", "roc", "rs_pct", "prox20d", "dist_sma50", "dist_sma200", "macd_diff"]

    def col(rows, k):
        vals = [r[k] for r in rows if r[k] is not None]
        return (mean(vals), median(vals)) if vals else (float("nan"), float("nan"))

    print(
        f"\n{'feature':<12} {'TP mean':>9} {'TP med':>8} | {'FP mean':>9} {'FP med':>8}  <-- discriminators"
    )
    for k in keys:
        tm, tmd = col(tps, k)
        fm, fmd = col(fps, k)
        flag = "  <===" if abs((tm or 0) - (fm or 0)) > max(2.0, 0.15 * abs(tm or 1)) else ""
        print(f"{k:<12} {tm:9.1f} {tmd:8.1f} | {fm:9.1f} {fmd:8.1f}{flag}")

    print("\nWorst FPs (highest score, lowest gain):")
    for r in sorted(fps, key=lambda x: (-x["score"], x["gain"]))[:12]:
        print(
            f"  {r['ticker']:<6} {r['date']} score={r['score']} gain={r['gain']:+.1f}% "
            f"rsi={r['rsi']:.0f} roc={r['roc']:+.1f} rs_pct={r['rs_pct']:.0f} "
            f"dist50={r['dist_sma50']:+.1f}% prox={r['prox20d']:.0f}"
        )

    # --- Candidate exclusion rules: which removes more FP than TP? ---
    def g(r, k, d=0.0):
        v = r.get(k)
        return d if v is None else v

    rules = {
        "rsi>=70 (overbought)": lambda r: g(r, "rsi") >= 70,
        "dist50>=12 (very extended)": lambda r: g(r, "dist_sma50") >= 12,
        "roc>=12 (parabolic)": lambda r: g(r, "roc") >= 12,
        "prox>=99 & rsi>=68": lambda r: g(r, "prox20d") >= 99 and g(r, "rsi") >= 68,
        "prox>=99 & rsi>=68 & dist50>=8": lambda r: g(r, "prox20d") >= 99
        and g(r, "rsi") >= 68
        and g(r, "dist_sma50") >= 8,
        "rsi>=68 & dist50>=10": lambda r: g(r, "rsi") >= 68 and g(r, "dist_sma50") >= 10,
        "rsi>=72 OR dist50>=15": lambda r: g(r, "rsi") >= 72 or g(r, "dist_sma50") >= 15,
        "rs_pct<50 (not a leader)": lambda r: g(r, "rs_pct") < 50,
        "rs_pct<70": lambda r: g(r, "rs_pct") < 70,
    }
    print(f"\n{'rule':<34} {'TP_rm':>6} {'FP_rm':>6} {'kept_prec':>10} {'kept_TP':>8}")
    for name, fn in rules.items():
        tp_rm = sum(1 for r in tps if fn(r))
        fp_rm = sum(1 for r in fps if fn(r))
        kept_tp = len(tps) - tp_rm
        kept_fp = len(fps) - fp_rm
        prec = kept_tp / (kept_tp + kept_fp) if (kept_tp + kept_fp) else 0.0
        print(f"{name:<34} {tp_rm:6d} {fp_rm:6d} {prec:9.1%} {kept_tp:8d}")


if __name__ == "__main__":
    asyncio.run(main())
