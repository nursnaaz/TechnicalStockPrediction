# V3 Validation Results (Task 4.4)

Live Polygon backtests of the implemented V3 engine via `backend/validate_v3.py`.
Confusion matrix = regime-aware predicted-bullish (BUY iff regime tradeable AND
score ≥ regime threshold) vs actual `max_gain ≥ 5%` over a 30-day horizon.

> **Methodology note:** the confusion matrix counts only **hard-filter-passing**
> tickers (hard-filter-failed names are excluded before scoring). Precision
> (TP/(TP+FP)) is unaffected by this; recall is measured among analyzable tickers.

## V1 — In-sample (105 halal tickers × 5 dates)

| Date | Regime | Trades | BUYs | TP | FP | FN | TN | Precision | Recall |
|------|--------|-------:|-----:|---:|---:|---:|---:|----------:|-------:|
| 2024-04-15 | bullish | 39 | 4 | 4 | 0 | 22 | 13 | 100% | 15% |
| 2024-08-01 | bullish | 39 | 15 | 11 | 4 | 21 | 3 | 73% | 34% |
| 2024-11-15 | bullish | 43 | 20 | 19 | 1 | 15 | 8 | 95% | 56% |
| 2025-02-01 | bullish | 38 | 24 | 15 | 9 | 8 | 6 | 62% | 65% |
| 2025-05-01 | **bearish** | 16 | **0** | 0 | 0 | 11 | 5 | — | — |
| **AGG** | | 175 | 49 | 49 | 14 | 77 | 35 | **77.8%** | **38.9%** |

## V3 — Out-of-sample (105 halal tickers × 5 NEW dates)

| Date | Regime | Trades | BUYs | TP | FP | FN | TN | Precision | Recall |
|------|--------|-------:|-----:|---:|---:|---:|---:|----------:|-------:|
| 2024-03-01 | bullish | 58 | 27 | 11 | 16 | 11 | 20 | 41% | 50% |
| 2024-07-01 | bullish | 47 | 13 | 7 | 6 | 28 | 6 | 54% | 20% |
| 2024-10-15 | bullish | 48 | 17 | 11 | 6 | 15 | 16 | 65% | 42% |
| 2025-04-01 | **bearish** | 17 | **0** | 0 | 0 | 7 | 10 | — | — |
| 2025-06-01 | bullish | 20 | 10 | 8 | 2 | 6 | 4 | 80% | 57% |
| **AGG** | | 190 | 37 | 37 | 30 | 67 | 56 | **55.2%** | **35.6%** |

## V2 — March-2026 control (50 tickers)

Expected (per V3 plan): **0 BUYs** (assumed bearish). **Actual: BULLISH regime, 5 BUYs.**

## Findings (honest)

| Success criterion | Target | Actual | Met? |
|-------------------|--------|--------|------|
| In-sample precision | ≥ 85% | **77.8%** | ❌ (but > V2 baseline 71%) |
| Out-of-sample precision | ≥ 80% | **55.2%** | ❌ |
| March-2026 → 0 BUYs | 0 | 5 (bullish) | ❌ (premise wrong) |
| Recall in 35–45% band | 35–45% | 38.9% / 35.6% | ✅ |
| Regime gate catches real bears | — | 2025-04 & 2025-05 → 0 BUYs | ✅ |

1. **Recall is on target (35–39%)** — the hard filters + threshold correctly produce
   fewer, more selective signals, as designed.
2. **The regime gate works** — it fired bearish on the genuine 2025 corrections
   (2025-04-01, 2025-05-01) and emitted zero candidates there.
3. **The "March 2026 was bearish" premise is empirically false.** Real SPY data on
   2026-03-01 is *above* its 200-day SMA → bullish. The gate is behaving correctly;
   success criterion #3 was based on a projected/incorrect market assumption.
4. **Precision misses the 85%/80% targets.** In-sample 77.8% beats the V2 baseline
   (71%) but not the goal. Out-of-sample 55.2% is well below target and below the
   spec's own anti-overfit floor (**rule #4: OOS < 75% ⇒ the ruleset is overfit and
   should be simplified, NOT tuned to dates**).
5. The biggest precision leaks are the "peak"/early-cycle dates (2025-02-01 P=62%,
   2024-03-01 P=41%) — the extension/divergence penalties are not fully neutralising
   late-stage extended names.

## Recommendation

Do **not** parameter-tune to these dates (violates anti-overfitting rules). The
honest read: V3 improves selectivity and regime-awareness over V2, hits the recall
target, but does not reach the aspirational precision. Per the spec's own rule #4,
the next step is **simplification** of the ruleset (fewer, higher-conviction filters)
— a strategy decision for the user, not a code change. The comprehensive
threshold-sweep report (task 4.6) over the full halal universe would quantify the
best achievable precision/recall trade-off before any redesign.
