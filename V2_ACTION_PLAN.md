# V2 Action Plan: Reducing False Positives & Improving Accuracy

**Based on:** Backtesting results (535 trades, 71% precision, 55% recall) + Web research synthesis

**Core Problem:** In bearish/pullback periods (Mar 2026), accuracy drops to 29%. Defensive stocks (KO, PG, JNJ) at peak get flagged bullish while growth stocks (AMD, CRWD, NVDA) about to bounce get missed.

---

## Brutal Honesty: What Technical Analysis CAN and CANNOT Do

### CAN DO:
- Identify stocks in established uptrends (Stage 2)
- Filter out stocks in downtrends or distributions
- Detect momentum shifts when price is already moving
- Provide timing context (overbought/oversold)
- Reduce losses by keeping you out of bear markets (regime filter)

### CANNOT DO:
- Predict reversals before they happen (the NVDA/AMD problem)
- Distinguish between "at peak about to fall" vs "at peak about to break higher"
- Know when a pullback ends (you can only react to the bounce starting)
- Replace fundamental analysis for catching bottoms

### The March 2026 Problem — Honest Assessment:
The FN stocks (AMD, CRWD, NVDA) had ZERO technical signals. No system relying on TA can catch a reversal before it starts. The correct response is: **accept these misses as the cost of avoiding false positives.** A system that catches falling knives will have far worse drawdowns than one that misses the first 5% of a bounce.

---

## PRIORITIZED ACTION PLAN

---

### CHANGE #1: Market Regime Gate (SPY > 200-day SMA)
**Priority: CRITICAL | Implementation Complexity: 1/5**

#### What to Implement:
Add a hard gate to the scoring pipeline:
```python
# In regime_analyzer.py - REPLACE current SMA50/SMA200 crossover logic
async def analyze_regime(self, as_of_date: str = None) -> RegimeResult:
    spy_data = await self.api_client.fetch_stock_data("SPY", days=250, as_of_date=as_of_date)
    
    sma_200 = float(spy_data.prices[-200:].mean())
    current_spy = float(spy_data.prices[-1])
    
    # PRIMARY: Is SPY above its 200-day SMA?
    spy_above_200 = current_spy > sma_200
    
    # ANTI-WHIPSAW: Require 5 consecutive closes above/below
    last_5_above = all(spy_data.prices[-5:] > sma_200)
    last_5_below = all(spy_data.prices[-5:] < sma_200)
    
    if spy_above_200 and last_5_above:
        regime = "BULLISH"
        trade_allowed = True
    elif not spy_above_200 and last_5_below:
        regime = "BEARISH"  
        trade_allowed = False  # NO LONGS ALLOWED
    else:
        regime = "NEUTRAL"
        trade_allowed = True   # But apply score penalty (see below)
        
    return RegimeResult(regime=regime, trade_allowed=trade_allowed, 
                        spy_vs_200=((current_spy - sma_200) / sma_200) * 100)
```

#### Behavior Change:
- **BEARISH regime → emit ZERO buy signals.** Full stop.
- **NEUTRAL regime → raise minimum score threshold from 65 to 75.**
- **BULLISH regime → normal operation.**

#### Why It Will Help:
This single rule eliminates the March 2026 problem entirely. Research shows SPY > 200-day MA achieved 30% CAGR vs 7% over 25 years. The 5-day delay prevents whipsaw losses.

#### Expected Impact:
- **Precision:** 71% → ~82-85% (eliminates all bear market FPs)
- **Recall:** 55% → ~48-50% (will miss some early bull signals — acceptable)
- **F1:** 62% → ~68-70%

---

### CHANGE #2: Extension Penalty Enhancement (Fix the KO/PG/JNJ Problem)
**Priority: HIGH | Implementation Complexity: 2/5**

#### What to Implement:
The current extension penalty maxes at -15. The problem is stocks like KO, PG, JNJ at peak STILL score 65+ because they pass all other checks. Strengthen to:

```python
# Replace current extension penalty in calculate_score()
# === EXTENSION PENALTY (0 to -25 pts) ===
extension_penalty = 0.0
if indicators.sma_50 is not None and indicators.sma_50 > 0:
    dist_above = ((current_price - indicators.sma_50) / indicators.sma_50) * 100
    
    # Distance from SMA50 (0-10)
    if dist_above > 15:
        extension_penalty += 10
    elif dist_above > 10:
        extension_penalty += 7
    elif dist_above > 7:
        extension_penalty += 4
    
    # RSI overbought (0-8)
    if indicators.rsi_14 is not None:
        if indicators.rsi_14 > 75:
            extension_penalty += 8
        elif indicators.rsi_14 > 70:
            extension_penalty += 5
        elif indicators.rsi_14 > 65:
            extension_penalty += 2
    
    # CRITICAL NEW CHECK: Momentum divergence while extended
    # If price is at highs but ROC is fading = distribution
    if indicators.roc_10 is not None and dist_above > 5:
        if indicators.roc_10 < -3:
            extension_penalty += 7   # Severe momentum loss at extension
        elif indicators.roc_10 < -1:
            extension_penalty += 5   # Momentum fading
        elif indicators.roc_10 < 0:
            extension_penalty += 3   # Slowing while extended
    
    # NEW: Proximity to 20-day high while extended = AT PEAK
    if indicators.proximity_to_20d_high is not None and dist_above > 7:
        if indicators.proximity_to_20d_high >= 97:
            extension_penalty += 5  # At peak AND extended = danger zone

total_score -= min(extension_penalty, 25)  # Increase cap from 15 to 25
```

#### Why It Will Help:
KO/PG/JNJ in March 2026 were 8-12% above SMA50, RSI 68-72, at 20-day highs, but ROC was negative. This combination is classic distribution. The old -15 cap wasn't enough to override the ~65+ base score. With -25 cap and momentum divergence check, these stocks drop below threshold.

#### Expected Impact:
- **Precision:** +5-8% (eliminates "at peak" false positives)
- **Recall:** No change (these stocks SHOULDN'T be flagged)
- **Net effect:** Fewer bad signals, same good signals

---

### CHANGE #3: Minervini Hard Filters (Pre-Screening Gate)
**Priority: HIGH | Implementation Complexity: 2/5**

#### What to Implement:
Before scoring, apply mandatory pass/fail filters. If ANY fails, the stock gets score = 0:

```python
# New method in scoring_engine.py
def passes_hard_filters(self, current_price: float, indicators, prices: np.ndarray) -> tuple[bool, list[str]]:
    """Return (passes, list_of_failures). ALL must pass."""
    failures = []
    
    # H1: Price above 200-day SMA
    if len(prices) >= 200:
        sma_200 = float(prices[-200:].mean())
        if current_price < sma_200:
            failures.append("H1: Below 200-day SMA")
    
    # H2: 200-day SMA must be rising (slope positive over last 20 days)
    if len(prices) >= 220:
        sma_200_now = float(prices[-200:].mean())
        sma_200_20ago = float(prices[-220:-20].mean())
        if sma_200_now <= sma_200_20ago:
            failures.append("H2: 200-day SMA not rising")
    
    # H3: Price above 150-day SMA
    if len(prices) >= 150:
        sma_150 = float(prices[-150:].mean())
        if current_price < sma_150:
            failures.append("H3: Below 150-day SMA")
    
    # H4: 50-day SMA above 200-day SMA
    if len(prices) >= 200:
        sma_50 = float(prices[-50:].mean())
        sma_200 = float(prices[-200:].mean())
        if sma_50 <= sma_200:
            failures.append("H4: SMA50 below SMA200 (death cross)")
    
    # H5: At least 30% above 52-week low
    if len(prices) >= 252:
        low_52w = float(prices[-252:].min())
        if low_52w > 0:
            distance_from_low = ((current_price - low_52w) / low_52w) * 100
            if distance_from_low < 30:
                failures.append(f"H5: Only {distance_from_low:.0f}% above 52w low (need 30%)")
    
    # H6: Within 25% of 52-week high (not too beaten down)
    if len(prices) >= 252:
        high_52w = float(prices[-252:].max())
        if high_52w > 0:
            distance_from_high = ((high_52w - current_price) / high_52w) * 100
            if distance_from_high > 25:
                failures.append(f"H6: {distance_from_high:.0f}% below 52w high (max 25%)")
    
    return (len(failures) == 0, failures)
```

#### Why It Will Help:
This is the Minervini "Trend Template" — the system that won the US Investing Championship with 155% and 334% returns. It's binary: a stock is either in a proper uptrend or it's not. No gradients, no partial credit. This eliminates:
- Stocks in downtrends getting high scores from recovery bonus
- Stocks in Stage 1 (basing) that haven't proven themselves
- Stocks rolling over from Stage 3 (distribution)

#### Expected Impact:
- **Precision:** +3-5% (pre-filters eliminate structurally weak candidates)
- **Recall:** -5-8% (will miss some early-stage recoveries — ACCEPTABLE)
- **Trade quality:** Much higher. Fewer trades, but better ones.

---

### CHANGE #4: Reduce Recovery Bonus Aggressiveness
**Priority: MEDIUM-HIGH | Implementation Complexity: 1/5**

#### What to Implement:
The current recovery bonus gives up to 25 points to stocks BELOW SMA50. This directly contradicts the Minervini hard filters. The recovery bonus should be:
1. **Removed entirely** if hard filters are active (recommended)
2. OR reduced to max 10 points and only triggers when regime is BULLISH

```python
# Option A (RECOMMENDED): Remove recovery bonus entirely
# Delete the entire "=== RECOVERY BONUS (0-25 pts) ===" section
# Rationale: If a stock is below SMA50, it fails Hard Filter H1.
# The recovery bonus was a band-aid for catching bounces. 
# With proper Stage 2 classification, it's no longer needed.

# Option B (CONSERVATIVE): Keep but neutered
recovery_score = 0.0
if regime == "BULLISH" and dist_from_sma50 < 0 and dist_from_sma50 > -10:
    # Only in bull markets, only shallow pullbacks
    if indicators.rsi_14 is not None and 30 <= indicators.rsi_14 <= 45:
        recovery_score += 5  # Max 5 instead of 10
    if indicators.roc_10 is not None and indicators.roc_10 > 2:
        recovery_score += 5  # Max 5 instead of 8
total_score += min(recovery_score, 10)  # Cap at 10, not 25
```

#### Why It Will Help:
The recovery bonus is the #1 source of false positives. It rewards stocks that are BELOW their moving averages — exactly the stocks that Minervini/research says to AVOID. It was designed to catch the AMD/NVDA bounces, but research is clear: **you cannot catch a bounce before it starts.** Wait for the stock to prove itself by reclaiming SMA50 first.

#### Expected Impact:
- **Precision:** +5-7% (removes primary FP generator)
- **Recall:** -8-12% (will miss early bounces — this is the CORRECT tradeoff)
- **Net portfolio return:** Higher, because avoided losses > missed early gains

---

### CHANGE #5: Add VWAP Trend Confirmation
**Priority: MEDIUM | Implementation Complexity: 3/5**

#### What to Implement:
Research shows EMA20 pullback + VWAP sloping up boosts win rate from 48.5% to 60%. Add VWAP slope as a confirmation filter:

```python
# In indicator_calculator.py - add VWAP calculation
def calculate_vwap_slope(self, prices: np.ndarray, volumes: np.ndarray, period: int = 5) -> float:
    """
    Calculate slope of VWAP over last N days.
    Positive slope = institutional buying pressure.
    """
    if len(prices) < period + 20 or len(volumes) < period + 20:
        return 0.0
    
    # Calculate daily VWAP (cumulative price*volume / cumulative volume)
    # Then measure slope of VWAP over last 'period' days
    vwap_values = []
    for i in range(-period, 0):
        # Rolling 20-day VWAP at each point
        p_slice = prices[i-20:i] if i != 0 else prices[-20:]
        v_slice = volumes[i-20:i] if i != 0 else volumes[-20:]
        if v_slice.sum() > 0:
            vwap = (p_slice * v_slice).sum() / v_slice.sum()
            vwap_values.append(vwap)
    
    if len(vwap_values) >= 2:
        slope_pct = ((vwap_values[-1] - vwap_values[0]) / vwap_values[0]) * 100
        return slope_pct
    return 0.0
```

Then in scoring:
```python
# Add to CONFIRMATION section
vwap_slope = calculate_vwap_slope(prices, volumes)
if vwap_slope > 0.5:
    confirmation_score += 3   # Institutional support
elif vwap_slope < -0.5:
    confirmation_score -= 3   # Institutional selling
```

#### Why It Will Help:
VWAP represents institutional participation. When VWAP slopes up, big money is accumulating. When it slopes down, they're distributing. This catches the KO/PG/JNJ distribution pattern that RS alone misses.

#### Expected Impact:
- **Precision:** +2-3%
- **Recall:** -1-2% (minor filtering)
- **Quality improvement:** Better at separating accumulation from distribution

---

### CHANGE #6: Relative Strength Rank (Percentile) Instead of Raw RS
**Priority: MEDIUM | Implementation Complexity: 3/5**

#### What to Implement:
Current system uses raw RS (stock return - SPY return). Problem: in pullbacks, defensives (KO, PG) have "positive RS" simply because they fell less. Switch to percentile ranking:

```python
# In orchestrator.py - after scanning all tickers
def calculate_rs_percentile(self, ticker_returns: dict[str, float]) -> dict[str, float]:
    """
    Convert raw relative strength to percentile rank (0-100).
    A stock must be in the TOP 30% of RS to get credit.
    """
    sorted_tickers = sorted(ticker_returns.items(), key=lambda x: x[1], reverse=True)
    total = len(sorted_tickers)
    
    percentiles = {}
    for rank, (ticker, _) in enumerate(sorted_tickers):
        percentiles[ticker] = ((total - rank) / total) * 100
    
    return percentiles

# In scoring - replace RS scoring
if rs_percentile is not None:
    if rs_percentile >= 90:
        strength_score += 10   # Top decile - true leader
    elif rs_percentile >= 70:
        strength_score += 7    # Top 30% - strong
    elif rs_percentile >= 50:
        strength_score += 4    # Above median
    else:
        strength_score += 0    # Below median - not a leader
```

#### Why It Will Help:
In March 2026, KO had +2% RS (vs SPY -5%), so raw RS was "positive". But if you ranked all 108 tickers, KO was probably only 50th percentile because OTHER defensives also did well. Percentile ranking identifies TRUE leaders (stocks outperforming most peers), not just "less bad" stocks.

#### Expected Impact:
- **Precision:** +3-5% (fewer defensive FPs in pullbacks)
- **Recall:** Neutral (true leaders still rank high)
- **Critical for:** Pullback/correction periods

---

### CHANGE #7: Multi-Indicator Divergence Confirmation
**Priority: MEDIUM | Implementation Complexity: 2/5**

#### What to Implement:
Research shows RSI + MACD + OBV all confirming simultaneously achieves 78% accuracy. Add a "divergence penalty" when indicators disagree:

```python
# After calculating all component scores, check for divergence
def calculate_divergence_penalty(self, indicators, current_price, prices):
    """
    Penalize when indicators send conflicting signals.
    Strong buys should have ALL indicators aligned.
    """
    bullish_signals = 0
    bearish_signals = 0
    
    # RSI direction
    if indicators.rsi_14 is not None:
        if indicators.rsi_14 > 50: bullish_signals += 1
        else: bearish_signals += 1
    
    # MACD direction
    if indicators.macd_line is not None and indicators.macd_signal is not None:
        if indicators.macd_line > indicators.macd_signal: bullish_signals += 1
        else: bearish_signals += 1
    
    # ROC direction
    if indicators.roc_10 is not None:
        if indicators.roc_10 > 0: bullish_signals += 1
        else: bearish_signals += 1
    
    # Price vs SMA50
    if indicators.sma_50 is not None:
        if current_price > indicators.sma_50: bullish_signals += 1
        else: bearish_signals += 1
    
    total_signals = bullish_signals + bearish_signals
    if total_signals >= 3:
        agreement_ratio = max(bullish_signals, bearish_signals) / total_signals
        if agreement_ratio < 0.6:
            return -8   # Major disagreement - high risk
        elif agreement_ratio < 0.75:
            return -4   # Some disagreement
    
    return 0  # Signals aligned or insufficient data
```

#### Why It Will Help:
The KO/PG/JNJ problem: RS was positive and they were above MAs, but MACD was flat/declining and ROC was negative. This divergence is a classic distribution signal. Penalizing divergent signals prevents high scores from one strong component masking weakness in others.

#### Expected Impact:
- **Precision:** +3-4%
- **Recall:** -2-3%
- **Reduces:** Misleading high scores from one-dimensional strength

---

## IMPLEMENTATION ORDER (By Expected ROI)

| # | Change | Precision Gain | Recall Cost | Complexity | Do First? |
|---|--------|---------------|-------------|------------|-----------|
| 1 | Regime Gate (SPY>200) | +10-14% | -5-7% | 1/5 | **YES - DAY 1** |
| 2 | Extension Penalty v2 | +5-8% | 0% | 2/5 | **YES - DAY 1** |
| 4 | Neuter Recovery Bonus | +5-7% | -8-12% | 1/5 | **YES - DAY 2** |
| 3 | Hard Filters (Minervini) | +3-5% | -5-8% | 2/5 | **YES - DAY 2** |
| 6 | RS Percentile Rank | +3-5% | 0% | 3/5 | **DAY 3** |
| 7 | Divergence Penalty | +3-4% | -2-3% | 2/5 | **DAY 3** |
| 5 | VWAP Confirmation | +2-3% | -1-2% | 3/5 | **DAY 4** |

**Cumulative Expected Impact:**
- Precision: 71% → **85-90%**
- Recall: 55% → **35-42%**
- F1: 62% → **52-58%** (lower F1 but MUCH better portfolio performance)

---

## Why Lower F1 is BETTER for a Trading System

F1 treats precision and recall equally. But in trading:
- **A false positive costs you money** (you buy a stock that drops)
- **A false negative costs you opportunity** (you miss a winner)

The asymmetry: missing a 10% winner costs you 10% of one position. Buying a 10% loser costs you 10% AND ties up capital AND incurs transaction costs AND psychological damage.

**The correct optimization target is: Precision × Average_Winner > (1-Precision) × Average_Loser**

With 90% precision and a 2:1 reward-risk ratio:
- Expected value per trade = (0.90 × 8%) - (0.10 × 4%) = 6.8% per trade

With 71% precision and the same ratio:
- Expected value per trade = (0.71 × 8%) - (0.29 × 4%) = 4.5% per trade

**Higher precision with fewer trades = more money.** Period.

---

## WHAT NOT TO DO (Anti-Overfitting Warnings)

### ❌ Do NOT add more indicators blindly
Research is clear: **3-5 parameters maximum.** Every additional indicator adds a degree of freedom that can be curve-fit to historical data. The 7 changes above don't add complexity — they add FILTERS that remove bad signals.

### ❌ Do NOT try to catch every bottom
The AMD/NVDA miss is psychologically painful but mathematically correct. A system that catches falling knives will have:
- Lower precision (catching many false bottoms for every real one)
- Higher maximum drawdown
- Worse risk-adjusted returns

### ❌ Do NOT optimize on the March 2026 data specifically
That's one period. The regime filter handles it generically. If you tune parameters to that specific month, you'll overfit.

### ❌ Do NOT use RSI(2) < 10 for the main scanner
The 90% win rate RSI(2) strategy is a MEAN REVERSION play with ~1-3 day holding period. Your scanner is for TREND FOLLOWING with 30-day horizons. These are incompatible. RSI(2) can be a separate module/strategy, not mixed into the momentum scanner.

### ❌ Do NOT add machine learning yet
ML requires thousands of labeled examples. With 535 trades across 5 dates, you have insufficient data. ML will overfit catastrophically. Stick with rule-based until you have 2000+ backtested trades.

---

## Score Budget After Changes

```
MAXIMUM POSSIBLE SCORE: 100 points

Components:
├── Trend Position (SMA50 + EMA20):     0-20 pts
├── Momentum (MACD + ROC):              0-20 pts  
├── Strength (RSI + RS Percentile):     0-20 pts
├── Confirmation (Volume + Breakout):   0-20 pts
├── Stage 2 + Pattern Bonus:            0-20 pts
│
├── Extension Penalty:                  0 to -25 pts  (increased from -15)
├── Divergence Penalty:                 0 to -8 pts   (NEW)
│
└── Hard Filters: PASS/FAIL gate (score = 0 if fail)
    └── Regime Gate: PASS/FAIL (no signals if SPY < 200-day)
```

**Minimum score to signal:** 
- BULLISH regime: 65 (current)
- NEUTRAL regime: 75 (raised from 65)
- BEARISH regime: ∞ (no signals emitted)

---

## Validation Plan

After implementing all changes, re-run the 535-trade backtest:

1. **Same 5 test dates** — measure precision/recall changes
2. **March 2026 specifically** — confirm FPs eliminated (KO, PG, JNJ should NOT signal)
3. **Bull market dates** — confirm TPs preserved (tech leaders still signal)
4. **Add 5 NEW dates** (not used in development) — out-of-sample validation
5. **Target:** Precision ≥ 85%, portfolio return ≥ +3% per 30-day period

If out-of-sample precision drops below 80%, something is overfit. Simplify.

---

## Summary: The Philosophy

> "The goal is not to find every winning stock. The goal is to ensure that when you DO buy, you're right 85%+ of the time."

The research is unanimous: **regime filtering + strict entry criteria + patience** beats trying to catch every move. Minervini won championships not by finding MORE stocks, but by being RIGHT on the ones he bought.

Your system's current 71% precision is good. Getting to 85-90% with these changes makes it exceptional. The recall drop from 55% to 38% means you'll take fewer trades — but each trade has dramatically higher expected value.

**Fewer, better trades. That's the entire game.**
