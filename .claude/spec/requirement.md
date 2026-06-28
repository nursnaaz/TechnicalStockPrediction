# V3 Requirements — High-Precision Bullish Scanner

> **Source:** Derived from `V3_ACTION_PLAN.md`. This document restates the V3 action plan as a formal,
> numbered requirements specification (structured prose + tables). It is the first artifact in the V3
> spec set: **requirement.md → design.md → task.md**.
>
> **Format note:** Requirements use IDs **R1–R10**. Validation tests use **V1–V4**. These IDs are
> referenced by `design.md` (Correctness Properties) and `task.md` (`_Requirements:_` tags).

---

## 1. Context

### 1.1 Current State (V2 Engine)

| Metric | Value |
|--------|-------|
| Trades evaluated | 535 across 5 dates |
| Universe | 108 halal tickers |
| Horizon | 30 days |
| Precision | 71% |
| Recall | 55% |
| F1 | 62% |
| Portfolio return | +2.3% per 30-day period |

**Problem:** In bearish periods (e.g. March 2026) precision collapses to **25–30%** with 20+ false
positives. The V2 engine has no market-regime awareness and rewards structurally weak stocks (recovery
bonus), producing buy signals in down markets.

### 1.2 Goal

| Target | Value |
|--------|-------|
| Precision | 85–90% (when we say BUY, right 85%+ of the time) |
| False positives in bearish markets | Zero tolerance |
| Recall | 35–45% (accepted tradeoff for signal quality) |
| Portfolio return | +4–5% per 30-day period |

### 1.3 Philosophy

The V3 system is a **trend-following scanner, not a bottom-fishing tool**. We do not try to catch
bottoms. We wait for a stock to **prove itself** by reclaiming key moving averages in a confirmed
uptrend, then buy the first pullback. We accept missing oversold bounces as correct behavior.

---

## 2. Functional Requirements

The V3 upgrade is **7 changes across 4 phases**, expressed below as requirements R1–R7, plus three
data/infrastructure requirements (R8–R10) that the changes imply.

---

### R1: SPY 200-Day Market Regime Gate

**Phase:** 1 — **Change:** 1 · **Files:** `backend/core/regime_analyzer.py`, `backend/core/orchestrator.py`

**Goal:** Before scoring any stock, gate the entire scan on the broad market's trend. Eliminate ALL buy
signals when the market is in a confirmed downtrend.

**Logic:** Replace the current SMA50/SMA200 crossover with an **EMA21 + 200-day SMA gate** using
5-day persistence:

```
spy_above_200  = SPY_close > SMA200(SPY)
last_5_above   = all of last 5 SPY closes > SMA200
last_5_below   = all of last 5 SPY closes < SMA200
```

| Condition | Regime | Action | Score threshold |
|-----------|--------|--------|-----------------|
| `spy_above_200 AND last_5_above` | **BULLISH** | Normal scoring | **65** |
| `NOT spy_above_200 AND last_5_below` | **BEARISH** | **Return ZERO candidates, no scoring** | n/a |
| otherwise | **NEUTRAL** | Score, but raise threshold | **75** |

**Why:** Single most impactful change. Research shows ~30% CAGR vs SPY ~7% over 25 years from this one
rule. Eliminates false positives in bear markets at the source.

**Impact:** Precision **+10–14%**, Recall **−5–7%**.

**Validation:** Run the March 2026 backtest — it should return **0 candidates** (market was bearish).
See **V2** in §3.

---

### R2: Minervini Hard Filters (Pass/Fail Gate)

**Phase:** 2 — **Change:** 2 · **Files:** `backend/core/scoring_engine.py`, `backend/core/orchestrator.py`

**Goal:** Before scoring, apply 6 binary filters. **If ANY filter fails, the stock receives `score = 0`**
and is excluded from candidates. Implemented as `passes_hard_filters()`, called before
`calculate_enhanced_score()`.

| ID | Filter | Condition |
|----|--------|-----------|
| H1 | Above 200-day SMA | `current_price > SMA(200)` |
| H2 | 200-day SMA rising | `SMA(200) slope > 0 over last 20 bars` |
| H3 | Above 150-day SMA | `current_price > SMA(150)` |
| H4 | Golden cross | `SMA(50) > SMA(200)` |
| H5 | 30% above 52-week low | `current_price >= 1.30 * 52_week_low` |
| H6 | Within 25% of 52-week high | `current_price >= 0.75 * 52_week_high` |

**Why:** Minervini's Trend Template won the US Investing Championship twice (155% in 1997, 334% in
2021). A stock failing any check is not in a proper Stage 2 uptrend and should not be bought.

**Impact:** Precision **+3–5%**, Recall **−5–8%**.

**Validation:** KO, PG, JNJ on March 2026 should FAIL filter H2 (or be eliminated earlier by the R1
regime gate).

---

### R3: Remove Recovery Bonus

**Phase:** 2 — **Change:** 3 · **Files:** `backend/core/scoring_engine.py`

**Goal:** Delete the entire **"RECOVERY BONUS (0–25 pts)"** section from the scoring engine.

**Why:** The recovery bonus rewards stocks **below** their moving averages — directly contradicting the
R2 hard filters (which require price ABOVE SMA200 and SMA150). It was giving 15–25 points to
structurally weak stocks, a primary false-positive source. We cannot reliably catch bottoms; wait for
the stock to reclaim key MAs, then buy the first pullback in the new uptrend.

**Impact:** Precision **+5–7%**, Recall **−8–12%**.

**Validation:** Stocks like AMD (score 18) and CRWD (score 25) in March 2026 should now score **0** (fail
hard filters) instead of receiving recovery-bonus points.

---

### R4: Stronger Extension Penalty + Momentum Divergence

**Phase:** 2 — **Change:** 4 · **Files:** `backend/core/scoring_engine.py`

**Goal:** Increase the extension penalty cap from **−15 to −25** and add momentum-divergence detection
(price at highs while momentum fades).

**Logic:**

```
extension_penalty = 0

# Distance above SMA50 (0-10)
if dist_above_sma50 > 15%: penalty += 10
elif dist_above_sma50 > 10%: penalty += 7
elif dist_above_sma50 > 7%:  penalty += 4

# RSI overbought (0-8)
if RSI > 75: penalty += 8
elif RSI > 70: penalty += 5
elif RSI > 65: penalty += 2

# Momentum divergence: price extended but momentum fading (0-7)
if dist_above_sma50 > 5% AND ROC(10) < -3%: penalty += 7
elif dist_above_sma50 > 5% AND ROC(10) < -1%: penalty += 5
elif dist_above_sma50 > 5% AND ROC(10) < 0:  penalty += 3

total_score -= min(penalty, 25)
```

**Why:** Stocks like KO (score 73) and PG (score 72) in March 2026 were at peak with fading momentum.
The old −15 cap couldn't override their 65+ base scores. The −25 cap plus divergence detection drops
them below threshold.

**Impact:** Precision **+5–8%**, Recall **0%** (only affects overextended stocks).

---

### R5: Relative Strength Percentile Ranking

**Phase:** 3 — **Change:** 5 · **Files:** `backend/core/orchestrator.py`, `backend/core/scoring_engine.py`

**Goal:** Replace raw RS (`ticker_return − SPY_return`) with **percentile rank across the full universe**.

**Logic:**

```
# In orchestrator, after computing raw RS for all tickers:
all_rs = {ticker: indicators.relative_strength for all tickers}
sorted_rs = sorted(all_rs.values())
for ticker, rs in all_rs.items():
    percentile = (sorted_rs.index(rs) / len(sorted_rs)) * 100

# In scoring (strength component):
if rs_percentile >= 90: strength_score += 10   # Top decile leader
elif rs_percentile >= 70: strength_score += 7  # Top 30%
elif rs_percentile >= 50: strength_score += 4  # Above median
else: strength_score += 0                       # Below median = not a leader
```

**Why:** In March 2026, KO had raw RS = +2% (positive) but ranked ~50th percentile because ALL
defensives had positive RS. True leaders (e.g. AMD, NVDA when they turn) rank 90th+ percentile.
Percentile ranking separates "less bad" from "genuinely strong." This requires a **two-pass**
orchestrator: compute raw RS for all tickers first, derive percentiles, then score.

**Impact:** Precision **+3–5%**, Recall **neutral**.

---

### R6: Indicator Divergence Penalty

**Phase:** 3 — **Change:** 6 · **Files:** `backend/core/scoring_engine.py`

**Goal:** Penalize stocks where indicators send conflicting signals (distribution patterns).

**Logic:**

```
bullish_count = 0; bearish_count = 0
if RSI > 50:        bullish_count += 1 else: bearish_count += 1
if MACD > signal:   bullish_count += 1 else: bearish_count += 1
if ROC > 0:         bullish_count += 1 else: bearish_count += 1
if price > SMA50:   bullish_count += 1 else: bearish_count += 1

total = bullish_count + bearish_count
agreement = max(bullish_count, bearish_count) / total

if agreement < 0.6:    total_score -= 8   # Major disagreement (2-2 split, agreement 0.5)
elif agreement <= 0.75: total_score -= 4  # Some disagreement (3-1 split, agreement 0.75)
```

> ⚠️ **Correction (from spec review):** The action plan's original middle tier was `elif agreement <
> 0.75`. With exactly **four** binary signals, `agreement = max(bull,bear)/4` can only be
> `{0.5, 0.75, 1.0}`. A strict `< 0.75` makes the −4 tier **unreachable** (3-1 splits give exactly
> 0.75 and would score 0). The corrected rule uses `<= 0.75` so a 3-1 split correctly incurs −4.
> **None-handling:** only count a signal whose indicator is available; if fewer than 2 signals are
> available, skip the divergence penalty (denominator = number of available signals, not always 4).

**Why:** The KO/PG case: above SMA50 (bullish) + positive RS (bullish), but MACD flat (bearish) and ROC
negative (bearish) = 2 bullish + 2 bearish = 50% agreement. This penalty catches distribution.

**Impact:** Precision **+3–4%**, Recall **−2–3%**.

---

### R7: Score Budget Rebalance + Signal Thresholds

**Phase:** 4 — **Change:** 7 · **Files:** `backend/core/scoring_engine.py`

**Goal:** Adjust the overall score architecture to reflect the new components and apply regime-based
signal thresholds.

**Score structure (max 100 points):**

| Component (before penalties) | Points |
|------------------------------|--------|
| Trend Position (SMA50 + EMA20) | 0–20 |
| Momentum (MACD + ROC) | 0–20 |
| Strength (RSI + RS Percentile) | 0–20 |
| Confirmation (Volume + Breakout) | 0–20 |
| Stage 2 + Pattern Bonus | 0–20 |
| **Maximum** | **100** |

**Penalties:**

| Penalty | Range |
|---------|-------|
| Extension Penalty (R4) | 0 to −25 |
| Divergence Penalty (R6) | 0 to −8 |
| **Maximum penalty** | **−33** |

**Gates (binary, before scoring):**

| Gate | Effect |
|------|--------|
| Regime Gate (R1): SPY > 200-day SMA | else emit zero signals |
| Hard Filters (R2): 6 Minervini checks | else `score = 0` |

**Signal thresholds (after all scoring):**

| Regime | Rule |
|--------|------|
| BULLISH | `score >= 65` → BUY |
| NEUTRAL | `score >= 75` → BUY |
| BEARISH | NO signals emitted regardless of score |

> **Note:** The recovery bonus (0–25) present in V2 is removed (R3), so the component budget returns to
> the five 0–20 components shown above.

---

## 2A. Data & Infrastructure Requirements (implied by R1–R7)

> These were not separate "changes" in the action plan but are **required** for R1–R7 to be
> implementable. Captured explicitly so nothing is missed. (See the action plan's "Files To
> Create/Modify" table.)

### R8: New Indicators — SMA(150) and SMA(200)

**Files:** `backend/core/indicator_calculator.py`, `backend/core/models.py`

Add `SMA(150)` and `SMA(200)` to `IndicatorCalculator.calculate_all()`, and add `sma_150` and `sma_200`
fields to the `TechnicalIndicators` model. Required by H1, H3, H4 (R2) and the strength/trend logic.

### R9: 52-Week High/Low + History Sufficiency

**Files:** `backend/core/api_client.py`, `backend/core/orchestrator.py`, `backend/core/regime_analyzer.py`, `backend/core/indicator_calculator.py`, `backend/core/models.py`

Hard filters H5/H6 (R2) require the **52-week high and low**. These must be derived from price history
(or surfaced on `StockData`). The scan must have **≥ 252 trading days** of history so SMA(200), the
SMA(200) slope over 20 bars (R10), and 52-week extremes are all computable.

> 🛑 **BINDING FIX (from spec review — was a critical defect):** `fetch_stock_data(days=N)` computes
> `from_date = to_date - timedelta(days=N)`, i.e. **N is CALENDAR days, not trading bars.** The current
> `days=250` yields only **~178 trading bars** — too few for SMA(200) (needs 200), the 20-bar slope
> (needs 220), and 52-week extremes (needs 252). Left unfixed, **every** hard filter returns `None →
> fail`, so the scanner emits **zero candidates in all regimes** (not just BEARISH), and the regime
> gate's SPY SMA200 is incomputable (silently defaults to NEUTRAL). **Required:** raise the fetch window
> to **≈ 365 calendar days** (guarantees ≥252 trading bars) at **every** call site — per-ticker and SPY
> in `orchestrator.py`, plus the SPY fetch in `regime_analyzer.py` — and **assert `len(prices) >= 252`**
> before computing gates so any shortfall fails loudly instead of silently zeroing all candidates.

### R10: SMA(200) Slope

**Files:** `backend/core/indicator_calculator.py`

Compute the **SMA(200) slope over the last 20 bars** (rising/falling) for hard filter H2 (R2). This
requires the SMA(200) **series** (≥20 trailing SMA200 values), not just the latest value.

---

## 3. Validation Requirements

After implementing all changes, run the following tests.

### V1: In-Sample (same 5 dates)

| Parameter | Value |
|-----------|-------|
| Dates | 2024-04-15, 2024-08-01, 2024-11-15, 2025-02-01, 2025-05-01 |
| Tickers | Full 108 halal universe |
| Target | Precision **≥ 85%**, Portfolio return **> +3%** |

### V2: March 2026 (regime gate proof)

| Parameter | Value |
|-----------|-------|
| Date | 2026-03-01 |
| Tickers | Top 50 |
| Expected | **0 BUY signals** (regime gate blocks everything) |
| If gate doesn't fire | Check SPY position vs 200-day SMA |

### V3: Out-of-Sample (NEW dates, never used in development)

| Parameter | Value |
|-----------|-------|
| Dates | 2024-03-01, 2024-07-01, 2024-10-15, 2025-04-01, 2025-06-01 |
| Tickers | Full 108 halal universe |
| Target | Precision **≥ 80%** (some degradation expected on unseen data) |

### V4: Portfolio Simulation

| Parameter | Value |
|-----------|-------|
| Strategy | $10,000 per BUY signal, hold 30 days |
| Measure | Total P&L, win rate, avg winner vs avg loser |
| Target | Win rate **≥ 70%**, Reward:Risk **≥ 2:1** |

---

## 4. Anti-Overfitting Constraints

1. Do **NOT** add more than **7 total changes** in this iteration.
2. Do **NOT** tune parameters to specific dates (use the same logic for all periods).
3. Keep it simple: **3–5 parameters per component max**.
4. If out-of-sample precision drops below **75%**, something is overfit — simplify.
5. Do **NOT** add machine learning (insufficient data with 535 trades).
6. Test on dates **NOT** used during development (V3 above).

---

## 5. Accepted Limitations (Honest Tradeoffs)

1. We **WILL miss oversold bounces** (e.g. AMD/NVDA in March 2026). This is correct behavior.
2. We **WILL have fewer BUY signals** (maybe 15–25 per scan of 100 stocks vs current 50+).
3. In **BEARISH** regime, we emit **zero** signals. Users must wait for market recovery.
4. **Recall will be 35–45%** — we only catch the BEST setups, not all winners.
5. The system is a **TREND-FOLLOWING** scanner, **not a bottom-fishing** tool.

---

## 6. Success Criteria

The V3 engine is successful if:

1. Precision **≥ 85%** on in-sample data (V1).
2. Precision **≥ 80%** on out-of-sample data (V3).
3. March 2026 emits **0 BUY signals** (regime gate, V2).
4. Portfolio return **positive in 4/5** test periods.
5. **No single trade loses more than −10%** (hard-filter quality).
6. **All 200+ existing unit tests still pass** (or are updated).

---

## 7. Files to Create / Modify (Traceability)

| File | Action | Description | Requirements |
|------|--------|-------------|--------------|
| `backend/core/regime_analyzer.py` | Rewrite | SPY 200-day gate + EMA21 | R1 |
| `backend/core/scoring_engine.py` | Modify | Remove recovery bonus, strengthen extension, add divergence, add hard filters, RS percentile, score budget | R2, R3, R4, R5, R6, R7 |
| `backend/core/orchestrator.py` | Modify | Add regime gate check, two-pass RS percentile, hard-filter gate, regime threshold | R1, R2, R5, R7 |
| `backend/core/indicator_calculator.py` | Modify | Add SMA(150), SMA(200), SMA(200) slope, 52-week high/low | R8, R9, R10 |
| `backend/core/models.py` | Modify | Add `sma_150`, `sma_200` (and 52-week fields) to `TechnicalIndicators` | R8, R9 |
| `backend/tests/unit/test_scoring_engine.py` | Rewrite | New tests for hard filters + penalties + RS percentile | R2, R3, R4, R5, R6, R7 |
| `backend/tests/unit/test_regime_analyzer.py` | Rewrite | Test regime gate logic | R1 |
| `backend/backtest/engine.py` | Modify | Align predicted-bullish with regime-aware BUY logic | R7 (V1–V4) |

---

## 8. Timeline (from action plan)

| Phase | Work | Estimate |
|-------|------|----------|
| 1 | Regime Gate | 1 hour |
| 2 | Hard Filters + Remove Recovery + Extension | 2 hours |
| 3 | RS Percentile + Divergence | 1.5 hours |
| 4 | Rebalance + Validation | 1.5 hours |
| **Total** | | **~6 hours** implementation + testing |

---

## Appendix A: Research Sources

1. "I Tested 20 Trend-Based Regime Filters" — setup4alpha.substack.com (Jun 2025)
2. "200-Day Regime Change Signal: 30% CAGR vs SPY 7%" — papertoprofit.substack.com
3. "Multi-indicator divergence achieves 78% accuracy" — tradealgo.com
4. "EMA20 + VWAP: win rate 48% to 60%" — trader-dale.com
5. "RSI(2) strategy: 90% win rate with profit factor 4" — quantifiedstrategies.com
6. Mark Minervini methodology — US Investing Championship 155% (1997), 334% (2021)
7. Elder Triple Screen — multi-timeframe confirmation
8. "Keep strategies to 3–5 parameters to avoid overfitting" — tradealgo.com
9. "9 out of 10 backtests produce misleading results" — financial-hacker.com
