# V2 Development Plan: Enhanced Rules & Backtesting Framework

**Branch:** `feature/v2-enhanced-rules-backtesting`

**Goals:**
1. Implement Phoenix Agent technical rules from Initial_prompt.md
2. Add comprehensive backtesting framework to validate prediction accuracy
3. Enhance scoring system with research-backed improvements

---

## Part 1: Rule Enhancement Analysis

### Current V1 Implementation vs Phoenix Agent Spec

#### ✅ **What V1 Already Has:**
- ✅ Basic technical indicators: SMA(50), EMA(20), MACD, Volume, Relative Strength
- ✅ Simple scoring system (0-100)
- ✅ Market regime analysis (SPY-based)
- ✅ Ticker ranking
- ✅ FastAPI backend + React frontend
- ✅ SQLite persistence

#### ❌ **Missing from Phoenix Agent Spec (Priority for V2):**

##### **Critical Missing Components:**

1. **Pattern Detection (HIGH PRIORITY)**
   - VCP (Volatility Contraction Pattern) - Research shows VCP provides ~40-55% win rate
   - Darvas Box - Historical 35-45% win rate with proper volume confirmation
   - Flat Base - Effective in consolidation breakouts
   - Tight Flag - Short-term momentum continuation
   - **Action:** Implement all 4 patterns with confidence scoring

2. **Extended Indicators (HIGH PRIORITY)**
   - SMA 10, 20, 150, 200 (currently only have 50)
   - EMA 13-week (Elder system)
   - Weekly MACD (12/26/9)
   - RVOL (today's volume / 20d avg)
   - 52-week high & low
   - RS Rank (percentile vs SPY)
   - RMV15 (volatility percentile)
   - ATR(14) for stop calculation
   - MA slopes for trend confirmation
   - **Action:** Add all missing indicators

3. **Hard Filters (CRITICAL)**
   - H1: Close above 200-day SMA
   - H2: Distance above 52-week low ≥ 50%
   - H3: Distance below 52-week high ≤ 35%
   - H4: No close below 50-day SMA in last 5 sessions
   - H5: Earnings not within next 10 trading days
   - **Action:** Implement as pre-screening gates

4. **Stage 2 Classification (CRITICAL)**
   - Current: None
   - Required: `close > SMA50 > SMA200`, SMA slopes, distance from 52w high/low
   - **Action:** Implement Weinstein Stage Analysis

5. **Strategy Confluence (HIGH PRIORITY)**
   - Minervini Trend Template (10 checks, need ≥6) - Research: 155% annual return in '97 championship
   - Stine 30-Week Superstock
   - Elder Weekly Impulse (GREEN/RED/BLUE)
   - **Action:** Require ≥2 of 3 strategies to trigger

6. **Entry/Stop/Target Calculation (HIGH PRIORITY)**
   - Entry zone: pivot + 0.1% to pivot × 1.02
   - Stop: pattern_low or SMA50, with ATR floor
   - Risk per trade: ≤7%
   - Targets: T1 (1.0× base height), T2 (1.5× base height)
   - Position sizing: 1% account risk per trade
   - **Action:** Implement risk management framework

##### **Medium Priority Components:**

7. **Extension/Chase Guardrail**
   - Current: None
   - Required: Severity scoring for overextended moves
   - **Action:** Add extension detection to prevent buying at highs

8. **Concentration & Portfolio Caps**
   - Current: None
   - Required: Max 3 per sector, max 12% total portfolio exposure
   - **Action:** Add post-ranking filters

9. **Weekly Bar Resampling**
   - Current: Daily bars only
   - Required: Local resampling Monday-Friday for weekly indicators
   - **Action:** Implement weekly bar aggregation

##### **Lower Priority (Future):**

10. **Earnings Calendar Integration**
    - Massive API has earnings data
    - Prevent entries within 10 days of earnings
    
11. **Sector Classification**
    - Use Massive reference API for GICS sectors
    - Enable sector concentration limits

12. **IPO Age Filter**
    - Require ≥150 trading days of history
    - Ensures SMA200 is valid

---

## Part 2: Research-Backed Improvements

Based on recent financial research and my expertise as a quantitative analyst:

### **Key Research Findings (2024-2026):**

#### **1. RSI Optimization**
- **Finding:** RSI with 2-day lookback achieves 91% win rate on SPY (23,487 trades backtested)
- **Standard 14-day RSI:** 53% win rate
- **Recommendation:** Add RSI(2) and RSI(14) as additional indicators
- **Source:** Backtested data across 27 years (riskpublishing.com, 2024)

#### **2. MACD Limitations**
- **Finding:** MACD shows poor standalone performance (26% on 5-min, 3% on daily)
- **However:** MACD divergence on 4-hour/daily has 68% win rate when combined with RSI
- **Current Issue:** V1 uses MACD in isolation
- **Recommendation:** Use MACD histogram divergence + RSI confirmation instead of raw MACD
- **Source:** 606,422 tested trades (liberatedstocktrader.com, 2025)

#### **3. Volume Confirmation Critical**
- **Finding:** Breakouts with volume ≥1.5× average have 2-3× higher success rate
- **Current:** V1 checks volume above average (basic)
- **Recommendation:** Implement tiered volume scoring:
  - 1.5-2.0×: +10 points
  - 2.0-3.0×: +15 points
  - >3.0×: +20 points

#### **4. Pattern Confidence Scoring**
- **VCP Win Rate:** 40-55% when properly identified (Minervini data)
- **Darvas Box:** 35-45% with volume confirmation
- **Current:** No patterns implemented
- **Recommendation:** Weight pattern confidence heavily (20% of score as per Phoenix spec)

#### **5. Multi-Timeframe Analysis**
- **Finding:** Combining daily + weekly timeframes improves accuracy by 15-20%
- **Current:** Daily only
- **Recommendation:** Add weekly indicators (EMA13, MACD, Impulse)

### **Recommended Scoring Weights (Research-Backed):**

```python
# Phoenix Spec (Keep This)
COMPOSITE_SCORE_WEIGHTS = {
    'volume': 0.40,      # Research confirms volume is #1 predictor
    'structure': 0.30,   # MA alignment + stage
    'pattern': 0.20,     # VCP/Darvas/Base detection
    'rs': 0.10           # Relative strength vs SPY
}

# Final Ranking (Phoenix Spec)
FINAL_SCORE_WEIGHTS = {
    'composite_score': 0.40,
    'minervini_pass_count': 0.20,  # Research: 155% annual return
    'rmv15_inverse': 0.15,          # Lower volatility = more stable
    'rs_rank': 0.15,
    'elder_weekly': 0.10
}
```

### **New Indicators to Add (Based on Research):**

1. **RSI(2)** - Mean reversion signal (91% win rate)
2. **RSI(14)** - Standard momentum (53% win rate)
3. **Bollinger Bands** - Volatility squeeze detection
4. **ADX(14)** - Trend strength confirmation (filters choppy markets)
5. **Stochastic RSI** - Enhanced momentum signal

---

## Part 3: Backtesting Framework Design

### **Goal:**
Validate if our bullish predictions actually work by testing historical data.

### **Core Requirements:**

#### **1. Time-Travel Testing**
```
User Input: "Test date: 2025-01-15"
System:
  1. Reconstructs universe as of 2025-01-15
  2. Fetches ONLY data up to 2025-01-15 (no look-ahead)
  3. Runs scan with as_of=2025-01-15
  4. Generates bullish predictions
  5. Fetches actual price data for next 30 trading days
  6. Computes accuracy metrics
```

#### **2. Metrics to Track:**

**Per-Trade Metrics:**
- Entry price (at pivot)
- Actual high reached in next 30 days
- Actual low reached in next 30 days
- Final price at day 30
- Return %: `(final_price - entry_price) / entry_price * 100`
- Did it hit Target 1? (yes/no)
- Did it hit Target 2? (yes/no)
- Did it hit Stop? (yes/no)
- Maximum adverse excursion (MAE): worst drawdown before exit
- Maximum favorable excursion (MFE): best gain before exit

**Aggregate Metrics:**
- **Win Rate:** % of trades with positive return at day 30
- **Target 1 Hit Rate:** % reaching T1 within 30 days
- **Target 2 Hit Rate:** % reaching T2 within 30 days
- **Stop Hit Rate:** % hitting stop before targets
- **Average Winner:** Mean return of winning trades
- **Average Loser:** Mean return of losing trades
- **Reward-to-Risk Ratio:** Avg winner / Avg loser
- **Expectancy:** (Win% × Avg Win) - (Loss% × Avg Loss)
- **Sharpe Ratio:** Risk-adjusted return
- **Maximum Drawdown:** Worst peak-to-trough decline

#### **3. Backtesting Modes:**

**A. Single Date Backtest**
```bash
POST /backtest/single
{
  "as_of": "2025-01-15",
  "tickers": ["AAPL", "MSFT", "GOOGL"],  # Optional, or scan universe
  "horizon_days": 30
}
```

**B. Rolling Window Backtest**
```bash
POST /backtest/rolling
{
  "start_date": "2024-01-01",
  "end_date": "2025-12-31",
  "frequency": "monthly",  # Run scan once per month
  "horizon_days": 30
}
```

**C. Walk-Forward Optimization**
```bash
POST /backtest/walk-forward
{
  "train_period_days": 365,
  "test_period_days": 90,
  "step_days": 30,
  "optimize_params": ["min_score", "volume_weight", "pattern_confidence_threshold"]
}
```

#### **4. Implementation Architecture:**

```
backend/
├── backtest/
│   ├── __init__.py
│   ├── engine.py          # Core backtesting logic
│   ├── metrics.py         # Metric calculations
│   ├── universe.py        # Historical universe reconstruction
│   ├── forward_testing.py # Walk-forward optimization
│   └── reports.py         # HTML/PDF report generation
├── api/
│   └── backtest_endpoints.py  # /backtest/* routes
└── tests/
    └── backtest/
        ├── test_engine.py
        ├── test_metrics.py
        └── test_no_lookahead.py  # CRITICAL: Verify no future data leakage
```

#### **5. No Look-Ahead Validation (CRITICAL):**

Every backtest MUST verify:
```python
def validate_no_lookahead(scan_date, data_used):
    """
    Ensures no bar with date > scan_date is used in any calculation.
    This is the #1 silent bug in backtesting.
    """
    for ticker, bars in data_used.items():
        for bar in bars:
            assert bar['date'] <= scan_date, f"Look-ahead violation: {ticker} bar {bar['date']} > scan_date {scan_date}"
```

#### **6. Backtest Report Output:**

```json
{
  "backtest_id": "uuid",
  "config": {
    "start_date": "2024-01-01",
    "end_date": "2025-12-31",
    "horizon_days": 30,
    "mode": "rolling_monthly"
  },
  "summary": {
    "total_scans": 24,
    "total_candidates": 312,
    "total_trades_taken": 156,
    "win_rate": 0.423,
    "avg_winner": 8.2,
    "avg_loser": -4.1,
    "reward_risk": 2.0,
    "expectancy": 1.76,
    "sharpe_ratio": 1.23,
    "max_drawdown": -18.5,
    "target_1_hit_rate": 0.38,
    "target_2_hit_rate": 0.12,
    "stop_hit_rate": 0.29
  },
  "by_score_bucket": {
    "80-100": {"count": 23, "win_rate": 0.61, "avg_return": 12.3},
    "70-79": {"count": 45, "win_rate": 0.51, "avg_return": 7.8},
    "65-69": {"count": 88, "win_rate": 0.35, "avg_return": 3.2}
  },
  "by_pattern": {
    "VCP": {"count": 34, "win_rate": 0.52, "avg_return": 9.1},
    "Darvas": {"count": 28, "win_rate": 0.46, "avg_return": 6.8},
    "Flat_Base": {"count": 19, "win_rate": 0.42, "avg_return": 5.3},
    "No_Pattern": {"count": 75, "win_rate": 0.33, "avg_return": 2.1}
  },
  "by_strategy": {
    "Minervini": {"count": 67, "win_rate": 0.49, "avg_return": 8.7},
    "Stine": {"count": 52, "win_rate": 0.44, "avg_return": 6.9},
    "Elder": {"count": 45, "win_rate": 0.41, "avg_return": 5.8},
    "All_Three": {"count": 12, "win_rate": 0.67, "avg_return": 14.2}
  },
  "monthly_performance": [
    {"month": "2024-01", "trades": 8, "win_rate": 0.50, "return": 4.2},
    {"month": "2024-02", "trades": 6, "win_rate": 0.33, "return": -1.8},
    // ... 24 months
  ],
  "detailed_trades": [
    {
      "scan_date": "2024-01-15",
      "ticker": "NVDA",
      "entry_price": 168.50,
      "stop": 156.80,
      "target_1": 181.30,
      "target_2": 187.45,
      "bullish_score": 84,
      "pattern": "VCP",
      "strategies": ["Minervini", "Stine", "Elder"],
      "actual_high_30d": 189.20,
      "actual_low_30d": 164.30,
      "final_price_30d": 185.40,
      "return_pct": 10.0,
      "hit_target_1": true,
      "hit_target_2": true,
      "hit_stop": false,
      "mae_pct": -2.5,
      "mfe_pct": 12.3,
      "result": "WIN"
    }
  ]
}
```

---

## Part 4: Implementation Roadmap

### **Phase 1: Core Phoenix Rules (Week 1)**

**Priority 1 (Days 1-2):**
- [ ] Add missing indicators (SMA 10/20/150/200, EMA 13wk, RVOL, ATR, 52w high/low)
- [ ] Implement Hard Filters (H1-H5)
- [ ] Implement Stage 2 classification
- [ ] Add weekly bar resampling

**Priority 2 (Days 3-4):**
- [ ] Implement VCP pattern detection
- [ ] Implement Darvas Box pattern
- [ ] Implement Flat Base pattern
- [ ] Implement Tight Flag pattern
- [ ] Add pattern confidence scoring

**Priority 3 (Days 5-7):**
- [ ] Implement Minervini Trend Template (10 checks)
- [ ] Implement Stine 30-Week setup
- [ ] Implement Elder Weekly Impulse
- [ ] Add strategy confluence logic (≥2 of 3)

### **Phase 2: Risk Management (Week 2)**

**Days 8-9:**
- [ ] Implement entry zone calculation
- [ ] Implement stop calculation with ATR floor
- [ ] Implement T1/T2 target calculation
- [ ] Add risk % validation (≤7%)
- [ ] Add position sizing hints

**Days 10-11:**
- [ ] Implement extension/chase guardrail
- [ ] Add sector concentration cap
- [ ] Add portfolio risk cap
- [ ] Implement final scoring formula

### **Phase 3: Backtesting Framework (Week 3)**

**Days 12-14:**
- [ ] Build backtest engine core
- [ ] Implement historical universe reconstruction
- [ ] Add no-look-ahead validation
- [ ] Implement metric calculations

**Days 15-17:**
- [ ] Add single-date backtest endpoint
- [ ] Add rolling window backtest
- [ ] Build HTML report generator
- [ ] Add trade-by-trade analysis

**Days 18-19:**
- [ ] Run validation backtests on 2023-2024 data
- [ ] Compare V1 vs V2 accuracy
- [ ] Document calibration expectations

### **Phase 4: Research-Backed Enhancements (Week 4)**

**Days 20-21:**
- [ ] Add RSI(2) and RSI(14)
- [ ] Implement RSI divergence detection
- [ ] Add MACD histogram divergence
- [ ] Add Bollinger Bands
- [ ] Add ADX(14)

**Days 22-24:**
- [ ] Run comprehensive backtests with new indicators
- [ ] Optimize scoring weights using walk-forward
- [ ] Generate comparison reports (V1 vs V2 vs Research)
- [ ] Document final accuracy metrics

---

## Part 5: Expected Improvements

### **V1 Baseline (Current):**
- Simple 5-indicator scoring
- No pattern detection
- No strategy confluence
- No risk management
- **Expected Win Rate:** ~35-40% (unvalidated)

### **V2 Target (With Phoenix Rules):**
- 20+ indicators
- 4 pattern types with confidence
- 3-strategy confluence
- Full risk management
- **Target Win Rate:** 45-55% on high-confidence signals (score ≥80)
- **Target Expectancy:** 1.5-2.0 (positive expected value)
- **Target Sharpe:** >1.0 (risk-adjusted outperformance)

### **Validation Criteria:**
```
Success = {
  "win_rate_80_plus": >= 0.50,     # 50%+ on scores 80-100
  "win_rate_70_plus": >= 0.43,     # 43%+ on scores 70-100
  "target_1_hit": >= 0.40,          # 40%+ reach T1 within 30d
  "reward_risk": >= 1.8,            # Winners 1.8× bigger than losers
  "expectancy": > 1.0,              # Positive expected value
  "sharpe": >= 0.8                  # Acceptable risk-adjusted return
}
```

---

## Part 6: Testing Strategy

### **Unit Tests:**
- Each indicator calculation (with known inputs/outputs)
- Each pattern detection algorithm
- Each hard filter
- Stage 2 classification
- Strategy confluence logic
- Risk calculations

### **Integration Tests:**
- Full pipeline with Phoenix rules
- Backtest engine end-to-end
- No-look-ahead validation (CRITICAL)
- Historical universe reconstruction

### **Validation Tests:**
- Run V2 on known historical setups (e.g., NVDA 2024-Q1 VCP)
- Compare against published Minervini/Darvas results
- Verify scoring matches Phoenix spec examples

---

## Next Steps:

1. ✅ Create branch: `feature/v2-enhanced-rules-backtesting`
2. ✅ Document V2 plan (this file)
3. Create Kiro spec for V2 features
4. Begin Phase 1 implementation
5. Run baseline V1 backtest for comparison

**Estimated Timeline:** 4 weeks (80-100 hours)

**Key Success Metric:** V2 achieves ≥45% win rate on score ≥70 signals when backtested on 2023-2024 data.

---

**Content Attribution:** Research findings compiled from published backtesting data (riskpublishing.com, liberatedstocktrader.com, tradealgo.com, 2024-2026) and Minervini/Darvas published methodologies. All content paraphrased for compliance.
