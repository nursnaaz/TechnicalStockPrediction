"""
V3 validation harness (spec task 4.4).

Drives the BacktestEngine directly (no HTTP server) against live Polygon data to
measure precision/recall/F1 and portfolio behavior. Confusion matrix is computed
from the backtest's regime-aware predicted_bullish vs actual max_gain >= 5%.

Usage:
    python validate_v3.py smoke      # 1 date, ~12 tickers (connectivity + timing)
    python validate_v3.py v1         # in-sample 5 dates, full universe
    python validate_v3.py march      # 2026-03-01 bearish control (expect 0 BUYs)
    python validate_v3.py v3         # out-of-sample 5 dates
"""
import asyncio
import os
import sys

# Run standalone (`python scripts/validate_v3.py` from backend/) by putting backend/ on the path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.engine import BacktestEngine
from config import config
from core.api_client import RestApiClient
from core.indicator_calculator import IndicatorCalculator
from core.orchestrator import ScanOrchestrator
from core.ranking_service import RankingService
from core.regime_analyzer import MarketRegimeAnalyzer
from core.scoring_engine import ScoringEngine
from core.universe_builder import UniverseBuilder

# Halal universe (same 108-ish set used for V2's 535-trade baseline)
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
    "FIS",
    "FISV",
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
    "TEAM",
    "TSM",
    "IBM",
    "CL",
    "KMB",
    "HSY",
    "MDLZ",
    "CLX",
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
    "F",
    "GM",
    "ENPH",
    "FSLR",
]

SMOKE = UNIVERSE[:12]
V1_DATES = ["2024-04-15", "2024-08-01", "2024-11-15", "2025-02-01", "2025-05-01"]
V3_DATES = ["2024-03-01", "2024-07-01", "2024-10-15", "2025-04-01", "2025-06-01"]


def build_engine():
    api_client = RestApiClient(
        api_key=config.POLYGON_TOKEN,
        base_url=config.API_BASE_URL,
        max_concurrent=config.MAX_CONCURRENT_REQUESTS,
        max_retries=config.MAX_RETRIES,
    )
    orch = ScanOrchestrator(
        api_client=api_client,
        universe_builder=UniverseBuilder(),
        regime_analyzer=MarketRegimeAnalyzer(api_client),
        indicator_calc=IndicatorCalculator(),
        scoring_engine=ScoringEngine(),
        ranking_service=RankingService(),
    )
    return BacktestEngine(api_client, orch)


def _confusion(trades):
    tp = sum(1 for t in trades if t.get("predicted_bullish") and t.get("actually_went_up"))
    fp = sum(1 for t in trades if t.get("predicted_bullish") and not t.get("actually_went_up"))
    fn = sum(1 for t in trades if not t.get("predicted_bullish") and t.get("actually_went_up"))
    tn = sum(1 for t in trades if not t.get("predicted_bullish") and not t.get("actually_went_up"))
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return tp, fp, fn, tn, prec, rec, f1


async def run_dates(label, dates, tickers, horizon=30):
    engine = build_engine()
    agg = []
    print(f"\n=== {label}: {len(tickers)} tickers x {len(dates)} dates (horizon {horizon}d) ===")
    for d in dates:
        res = await engine.run_single_date_backtest(
            as_of_date=d, tickers=tickers, horizon_days=horizon
        )
        if res.get("status") != "completed":
            print(f"  {d}: {res.get('status')} {res.get('error','')}")
            continue
        analyzed = [
            t for t in res["trades"] if t.get("status") == "analyzed" or "predicted_bullish" in t
        ]
        regime = res.get("market_regime")
        regime = getattr(regime, "value", regime)
        buys = sum(1 for t in analyzed if t.get("predicted_bullish"))
        tp, fp, fn, tn, prec, rec, f1 = _confusion(analyzed)
        agg.extend(analyzed)
        print(
            f"  {d}: regime={regime:8s} trades={len(analyzed):3d} BUYs={buys:3d} "
            f"TP={tp} FP={fp} FN={fn} TN={tn} | P={prec:.0%} R={rec:.0%} F1={f1:.0%}"
        )
    if agg:
        tp, fp, fn, tn, prec, rec, f1 = _confusion(agg)
        print(
            f"  ---- AGG: trades={len(agg)} TP={tp} FP={fp} FN={fn} TN={tn} "
            f"| Precision={prec:.1%} Recall={rec:.1%} F1={f1:.1%}"
        )
    return agg


async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "smoke"
    if mode == "smoke":
        await run_dates("SMOKE", ["2025-02-01"], SMOKE)
    elif mode == "v1":
        await run_dates("V1 in-sample", V1_DATES, UNIVERSE)
    elif mode == "march":
        await run_dates("V2 March-2026 control", ["2026-03-01"], UNIVERSE[:50])
    elif mode == "v3":
        await run_dates("V3 out-of-sample", V3_DATES, UNIVERSE)
    else:
        print(f"unknown mode: {mode}")


if __name__ == "__main__":
    asyncio.run(main())
