# V3 Action Plan: High-Precision Bullish Scanner

## Current State (V2 Engine)

- **535 trades** across 5 dates, 108 halal tickers, 30-day horizon
- Precision: 71% | Recall: 55% | F1: 62%
- Portfolio return: +2.3% per 30-day period
- Problem: In bearish periods (Mar 2026), precision drops to 25-30% with 20+ false positives

## Goal

- Precision: 85-90% (when we say BUY, we are right 85%+ of the time)
- Zero tolerance for false positives in bearish markets
- Accept lower recall (35-45%) as tradeoff for higher quality signals
- Portfolio return: +4-5% per 30-day period

## Research Sources

- "I Tested 20 Trend-Based Regime Filters" (setup4alpha.substack.com, Jun 2025)
- "200-Day Regime Change Signal: 30% CAGR vs SPY 7%" (papertoprofit.substack.com)
- "Multi-indicator divergence achieves 78% accuracy" (tradealgo.com)
- "EMA20 + VWAP: win rate 48% to 60%" (trader-dale.com)
- "RSI(2) strategy: 90% win rate with profit factor 4" (quantifiedstrategies.com)
- Mark Minervini methodology: US Investing Championship 155% (1997), 334% (2021)
- Elder Triple Screen: multi-timeframe confirmation
- "Keep strategies to 3-5 parameters to avoid overfitting" (tradealgo.com)
- "9 out of 10 backtests produce misleading results" (financial-hacker.com)

---

## Implementation Plan (7 Changes, 4 Phases)

---

## Phase 1: Market Regime Gate (Day 1)

### Change 1: SPY 200-Day SMA Regime Filter

**What**: Before scoring any stock, check if SPY is above its 200-day SMA.
If SPY is below 200-day SMA for 5+ consecutive days, emit ZERO buy signals.

**Files to modify**:
- `backend/core/regime_analyzer.py` — Replace current SMA50/SMA200 crossover with EMA21 + 200-day gate
- `backend/core/orchestrator.py` — Add regime gate before scoring loop

**Logic**:
```
spy_above_200 = SPY_close > SMA200(SPY)
last_5_above = all last 5 SPY closes > SMA200

if spy_above_200 AND last_5_above:
    regime = BULLISH → normal scoring, threshold = 65
elif NOT spy_above_200 AND last 5 below:
    regime = BEARISH → return ZERO candidates, no scoring
else:
    regime = NEUTRAL → score but raise threshold to 75
```

**Why**: Single most impactful change. Eliminates ALL false positives in bear markets.
Research shows 30% CAGR vs 7% over 25 years just from this one rule.

**Expected impact**: Precision +10-14%, Recall -5-7%

**Validation**: Run March 2026 backtest. Should return 0 candidates (market was bearish).

---

## Phase 2: Eliminate False Positives (Day 2)

### Change 2: Minervini Hard Filters (Pass/Fail Gate)

**What**: Before scoring, apply 6 binary filters. If ANY fails, stock gets score=0.

**Files to modify**:
- `backend/core/scoring_engine.py` — Add `passes_hard_filters()` method
- `backend/core/orchestrator.py` — Call hard filters before `calculate_enhanced_score()`

**Filters**:
```
H1: current_price > SMA(200)
H2: SMA(200) slope > 0 over last 20 bars (rising)
H3: current_price > SMA(150)
H4: SMA(50) > SMA(200) (golden cross)
H5: current_price >= 1.30 * 52_week_low (30% above low)
H6: current_price >= 0.75 * 52_week_high (within 25% of high)
```

**Why**: Minervini's Trend Template won the US Investing Championship twice. If a stock fails any check, it's not in a proper Stage 2 uptrend and should not be bought.

**Expected impact**: Precision +3-5%, Recall -5-8%

**Validation**: KO, PG, JNJ on March 2026 should FAIL filter H2 or be eliminated by regime gate.

---

### Change 3: Remove Recovery Bonus

**What**: Delete the entire recovery bonus section from the scoring engine.

**Files to modify**:
- `backend/core/scoring_engine.py` — Remove the "RECOVERY BONUS (0-25 pts)" section

**Why**: The recovery bonus rewards stocks BELOW their moving averages. This directly contradicts Minervini hard filters (which require price ABOVE SMA200 and SMA150). The bonus was causing false positives by giving 15-25 points to structurally weak stocks.

Research is clear: you cannot reliably catch bottoms. Wait for the stock to PROVE itself by reclaiming key MAs, then buy the first pullback in the new uptrend.

**Expected impact**: Precision +5-7%, Recall -8-12%

**Validation**: Stocks like AMD (score=18), CRWD (score=25) in Mar 2026 should now score 0 (fail hard filters) rather than getting recovery bonus points.

---

### Change 4: Stronger Extension Penalty

**What**: Increase extension penalty cap from -15 to -25. Add momentum divergence detection.

**Files to modify**:
- `backend/core/scoring_engine.py` — Rewrite extension penalty section

**New logic**:
```
extension_penalty = 0

# Distance above SMA50 (0-10)
if dist_above_sma50 > 15%: penalty += 10
elif dist_above_sma50 > 10%: penalty += 7
elif dist_above_sma50 > 7%: penalty += 4

# RSI overbought (0-8)
if RSI > 75: penalty += 8
elif RSI > 70: penalty += 5
elif RSI > 65: penalty += 2

# MOMENTUM DIVERGENCE: price at highs but momentum fading (0-7)
if dist_above_sma50 > 5% AND ROC(10) < -3%: penalty += 7
elif dist_above_sma50 > 5% AND ROC(10) < -1%: penalty += 5
elif dist_above_sma50 > 5% AND ROC(10) < 0: penalty += 3

total_score -= min(penalty, 25)
```

**Why**: Stocks like KO (score 73) and PG (score 72) in March 2026 were at peak with fading momentum. The old -15 cap wasn't enough to override their 65+ base scores. With -25 cap and divergence detection, these drop below threshold.

**Expected impact**: Precision +5-8%, Recall 0% (only affects overextended stocks)

---

## Phase 3: Improve Signal Quality (Day 3)

### Change 5: Relative Strength Percentile Ranking

**What**: Replace raw RS (ticker_return - SPY_return) with percentile rank across the full universe.

**Files to modify**:
- `backend/core/orchestrator.py` — After scoring all tickers, calculate RS percentile
- `backend/core/scoring_engine.py` — Accept rs_percentile parameter

**Logic**:
```
# In orchestrator, after computing raw RS for all tickers:
all_rs = {ticker: indicators.relative_strength for all tickers}
sorted_rs = sorted(all_rs.values())
for ticker, rs in all_rs.items():
    percentile = (sorted_rs.index(rs) / len(sorted_rs)) * 100
    
# In scoring:
if rs_percentile >= 90: strength_score += 10  # Top decile leader
elif rs_percentile >= 70: strength_score += 7  # Top 30%
elif rs_percentile >= 50: strength_score += 4  # Above median
else: strength_score += 0  # Below median = not a leader
```

**Why**: In March 2026, KO had raw RS = +2% (positive). But ranked against 108 tickers, it was probably 50th percentile because ALL defensives had positive RS. True leaders (AMD, NVDA when they turn) rank 90th+ percentile. Percentile ranking separates "less bad" from "genuinely strong."

**Expected impact**: Precision +3-5%, Recall neutral

---

### Change 6: Indicator Divergence Penalty

**What**: Penalize stocks where indicators send conflicting signals.

**Files to modify**:
- `backend/core/scoring_engine.py` — Add divergence check after component scoring

**Logic**:
```
bullish_count = 0
bearish_count = 0

if RSI > 50: bullish_count += 1 else: bearish_count += 1
if MACD > signal: bullish_count += 1 else: bearish_count += 1
if ROC > 0: bullish_count += 1 else: bearish_count += 1
if price > SMA50: bullish_count += 1 else: bearish_count += 1

total = bullish_count + bearish_count
agreement = max(bullish_count, bearish_count) / total

if agreement < 0.6: total_score -= 8   # Major disagreement
elif agreement < 0.75: total_score -= 4  # Some disagreement
```

**Why**: The KO/PG problem in detail: they were above SMA50 (bullish) with positive RS (bullish), but MACD was flat (bearish) and ROC was negative (bearish). That's 2 bullish + 2 bearish = 50% agreement. This divergence penalty catches distribution patterns.

**Expected impact**: Precision +3-4%, Recall -2-3%

---

## Phase 4: Advanced Confirmation (Day 4)

### Change 7: Score Budget Rebalance

**What**: Adjust the overall score architecture to reflect the new components.

**New score structure**:
```
MAXIMUM POSSIBLE: 100 points

Components (before penalties):
├── Trend Position (SMA50 + EMA20):     0-20 pts
├── Momentum (MACD + ROC):              0-20 pts
├── Strength (RSI + RS Percentile):     0-20 pts
├── Confirmation (Volume + Breakout):   0-20 pts
├── Stage 2 + Pattern Bonus:            0-20 pts
│                                       --------
│                                       Max: 100

Penalties:
├── Extension Penalty:                  0 to -25 pts
├── Divergence Penalty:                 0 to -8 pts
│                                       --------
│                                       Max penalty: -33

Gates (binary, before scoring):
├── Regime Gate: SPY > 200-day SMA (or emit zero signals)
├── Hard Filters: 6 Minervini checks (or score = 0)
```

**Signal thresholds** (after all scoring):
- BULLISH regime: score >= 65 → BUY signal
- NEUTRAL regime: score >= 75 → BUY signal
- BEARISH regime: NO signals emitted regardless of score

---

## Validation Plan

After implementing all 7 changes, run the following tests:

### Test 1: Same 5 dates (in-sample)
```
Dates: 2024-04-15, 2024-08-01, 2024-11-15, 2025-02-01, 2025-05-01
Tickers: Full 108 halal universe
Target: Precision >= 85%, Portfolio return > +3%
```

### Test 2: March 2026 specifically
```
Date: 2026-03-01, Top 50 tickers
Expected: 0 BUY signals (regime gate should block everything)
If regime gate doesn't fire, check SPY position vs 200-day SMA
```

### Test 3: Out-of-sample (NEW dates, never used in development)
```
Dates: 2024-03-01, 2024-07-01, 2024-10-15, 2025-04-01, 2025-06-01
Tickers: Full 108 halal universe
Target: Precision >= 80% (some degradation expected on unseen data)
```

### Test 4: Portfolio simulation
```
Strategy: $10,000 per BUY signal, hold 30 days
Measure: Total P&L, win rate, avg winner vs avg loser
Target: Win rate >= 70%, Reward:Risk >= 2:1
```

---

## Anti-Overfitting Rules

1. Do NOT add more than 7 total changes in this iteration
2. Do NOT tune parameters to specific dates (use the same logic for all periods)
3. Keep it simple: 3-5 parameters per component max
4. If out-of-sample precision drops below 75%, something is overfit — simplify
5. Do NOT add machine learning (insufficient data with 535 trades)
6. Test on dates NOT used during development (Test 3 above)

---

## What We Accept (Honest Limitations)

1. We WILL miss oversold bounces (AMD/NVDA in Mar 2026). This is correct behavior.
2. We WILL have fewer BUY signals (maybe 15-25 per scan of 100 stocks vs current 50+)
3. In BEARISH regime, we emit zero signals. Users must wait for market recovery.
4. Recall will be 35-45% — we only catch the BEST setups, not all winners
5. The system is a TREND-FOLLOWING scanner, not a bottom-fishing tool

---

## Files To Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `backend/core/regime_analyzer.py` | Rewrite | SPY 200-day gate + EMA21 |
| `backend/core/scoring_engine.py` | Modify | Remove recovery bonus, strengthen extension, add divergence, add hard filters |
| `backend/core/orchestrator.py` | Modify | Add regime gate check, pass rs_percentile |
| `backend/core/indicator_calculator.py` | Modify | Add SMA(150), SMA(200) calculations |
| `backend/core/models.py` | Modify | Add sma_150, sma_200 to TechnicalIndicators |
| `backend/tests/unit/test_scoring_engine.py` | Rewrite | New tests for hard filters + penalties |
| `backend/tests/unit/test_regime_analyzer.py` | Rewrite | Test regime gate logic |

---

## Timeline

- Phase 1 (Regime Gate): 1 hour
- Phase 2 (Hard Filters + Remove Recovery + Extension): 2 hours
- Phase 3 (RS Percentile + Divergence): 1.5 hours
- Phase 4 (Rebalance + Validation): 1.5 hours
- Total: ~6 hours of implementation + testing

---

## Success Criteria

The V3 engine is successful if:
1. Precision >= 85% on in-sample data
2. Precision >= 80% on out-of-sample data
3. March 2026 emits 0 BUY signals (regime gate)
4. Portfolio return positive in 4/5 test periods
5. No single trade loses more than -10% (hard filter quality)
6. All 200+ existing unit tests still pass (or are updated)
