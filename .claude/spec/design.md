# V3 Design Document — High-Precision Bullish Scanner

> **Source:** Implements `requirement.md` (R1–R10). Mirrors the house format used in
> `.kiro/specs/bullish-stock-scanner/design.md` (Component Specifications + numbered Correctness
> Properties tagged `Validates: Rn`). Scoped to the **V3 delta** — unchanged V1/V2 pipeline pieces are
> described only as needed for context.

---

## 1. Overview

V3 transforms the V2 gradient scanner into a **precision-first, trend-following** scanner. The core
design change is that **scoring is now bracketed by two binary gates** and one cross-universe ranking
pass:

1. A **market-regime gate** (R1) that can short-circuit the entire scan (zero candidates in bear markets).
2. A **Minervini hard-filter gate** (R2) that zeroes any stock not in a proper Stage 2 uptrend.
3. A **two-pass RS-percentile** computation (R5) so strength is ranked across the universe, not absolute.

The scoring engine itself is rebalanced: the recovery bonus is removed (R3), the extension penalty is
strengthened with momentum divergence (R4), an indicator-divergence penalty is added (R6), and
regime-dependent BUY thresholds are applied (R7). New indicators (SMA150/200, SMA200 slope, 52-week
high/low) feed the gates (R8–R10).

**Design philosophy:** prove the uptrend, then buy the first pullback; never bottom-fish. Fewer, higher
quality signals. Zero signals in a confirmed downtrend.

---

## 2. Architecture

### 2.1 Pipeline (V3)

The existing `ScanOrchestrator` pipeline is augmented with gates (decision points) and a two-pass
structure:

```
                         ┌─────────────────────────────┐
                         │   ScanOrchestrator.execute   │
                         └─────────────────────────────┘
                                       │
                          ┌────────────▼────────────┐
                          │  R1: Regime Gate (SPY)   │
                          │  EMA21 + SMA200 + 5-day  │
                          └────────────┬────────────┘
                 BEARISH ◄─────────────┤
            (return ZERO candidates)   │ BULLISH(thr=65) / NEUTRAL(thr=75)
                                       │
                          ┌────────────▼─────────────────────────┐
                          │  PASS 1: per ticker                   │
                          │   fetch (≥252 bars) → indicators      │
                          │   (+SMA150/200, slope, 52wk hi/lo)    │
                          │   compute raw relative_strength       │
                          └────────────┬─────────────────────────┘
                                       │
                          ┌────────────▼─────────────────────────┐
                          │  R5: RS percentile across universe    │
                          └────────────┬─────────────────────────┘
                                       │
                          ┌────────────▼─────────────────────────┐
                          │  PASS 2: per ticker                   │
                          │   R2: passes_hard_filters()?          │
                          │     NO → score = 0 (excluded)         │
                          │     YES ↓                             │
                          │   calculate_enhanced_score()          │
                          │     trend/momentum/strength(+RS pct)/ │
                          │     confirmation/stage+pattern        │
                          │     − extension penalty (R4, ≤−25)    │
                          │     − divergence penalty (R6, ≤−8)    │
                          └────────────┬─────────────────────────┘
                                       │
                          ┌────────────▼─────────────────────────┐
                          │  R7: BUY iff score ≥ regime threshold │
                          │  rank candidates (RankingService)     │
                          └───────────────────────────────────────┘
```

> **Two-pass requirement (R5):** RS percentile needs every ticker's raw RS before any single ticker can
> be scored. Pass 1 fetches + computes indicators (incl. raw RS); the percentile is derived across the
> universe; Pass 2 applies hard filters and scoring with `rs_percentile` available.

### 2.2 Where each requirement lives

| Layer | Module | Requirements |
|-------|--------|--------------|
| Regime gate | `core/regime_analyzer.py` (rewrite), consumed in `core/orchestrator.py` | R1 |
| Indicators | `core/indicator_calculator.py`, `core/models.py` | R8, R9, R10 |
| Hard filters | `core/scoring_engine.py` (`passes_hard_filters`), called in `core/orchestrator.py` | R2 |
| Scoring changes | `core/scoring_engine.py` | R3, R4, R5, R6, R7 |
| Two-pass + thresholds | `core/orchestrator.py` | R1, R5, R7 |
| Validation | `backtest/engine.py`, `backtest/metrics.py` | V1–V4 |

---

## 3. Component Specifications

### 3.1 MarketRegimeAnalyzer (rewrite) — R1

**Current:** `analyze_regime(as_of_date=None) -> MarketRegime` using SPY SMA50-vs-SMA200 crossover.

**V3 contract:** return regime **plus** the score threshold and an emit flag, so the orchestrator can
gate and threshold in one place.

```python
from dataclasses import dataclass

@dataclass
class RegimeResult:
    regime: MarketRegime      # BULLISH / BEARISH / NEUTRAL
    threshold: int            # 65 (BULLISH), 75 (NEUTRAL); ignored when BEARISH
    emit_signals: bool        # False in BEARISH → orchestrator returns zero candidates

class MarketRegimeAnalyzer:
    def __init__(self, api_client: RestApiClient): ...

    async def analyze_regime(self, as_of_date: str | None = None) -> RegimeResult:
        """
        Fetch SPY (≥252 bars up to as_of_date), compute SMA200 series and EMA21.
        Apply 5-day persistence:
          spy_above_200 = SPY_close > SMA200
          last_5_above  = all(last 5 closes > SMA200)
          last_5_below  = all(last 5 closes < SMA200)
        BULLISH  if spy_above_200 and last_5_above  → threshold 65, emit True
        BEARISH  if (not spy_above_200) and last_5_below → emit False
        NEUTRAL  otherwise → threshold 75, emit True
        On API failure: default to NEUTRAL (emit True, threshold 75).
        """
```

**Implementation notes:**
- EMA21 is computed for trend confirmation per the action plan ("EMA21 + 200-day gate"); the gating
  decision is driven by SPY vs SMA200 with 5-day persistence. (EMA21's exact role is a refinement; see
  Open Question OQ-3.)
- Keep `as_of_date` point-in-time support (no look-ahead).
- **Backward-compat impact:** return type changes from `MarketRegime` to `RegimeResult`; `orchestrator`
  and `tests/unit/test_regime_analyzer.py` must be updated.

### 3.2 IndicatorCalculator (extend) — R8, R9, R10

Add new indicators to `calculate_all()`, reusing the existing static helpers (`calculate_sma`, etc.):

```python
def calculate_all(self, stock_data, market_data) -> TechnicalIndicators:
    ...
    indicators.sma_150 = self.calculate_sma(stock_data.prices, 150)
    indicators.sma_200 = self.calculate_sma(stock_data.prices, 200)
    indicators.sma_200_slope = self._sma_slope(stock_data.prices, period=200, lookback=20)
    indicators.week52_high = float(np.max(stock_data.prices[-252:]))
    indicators.week52_low  = float(np.min(stock_data.prices[-252:]))
    ...

@staticmethod
def _sma_slope(prices, period: int, lookback: int = 20) -> Optional[float]:
    """Slope of the SMA(period) series over the last `lookback` bars.
    Returns SMA200[-1] - SMA200[-1-lookback] (or per-bar slope). > 0 means rising.
    Requires ≥ period + lookback bars; else None."""
```

**Implementation notes:**
- 🛑 **History sufficiency (R9) — BINDING (verified defect):** `fetch_stock_data(days=N)` uses
  `from_date = to_date - timedelta(days=N)`, so **N is CALENDAR days**. `days=250` → **~178 trading
  bars**, which makes SMA200 (≥200), the 20-bar slope (≥220), and 52-week extremes (≥252) all return
  `None` → every hard filter fails → **zero candidates in every regime** (and the SPY regime gate's
  SMA200 is incomputable). **Fix:** raise the fetch window to **≈365 calendar days** at all call sites
  (per-ticker + SPY in `orchestrator.py`; SPY fetch in `regime_analyzer.py`) and **assert
  `len(prices) >= 252`** before gate computation so shortfalls fail loudly. (Was OQ-1 — now resolved.)
- 52-week high/low derived from `prices[-252:]` (no `StockData` change strictly required); may also be
  stored on `StockData` if convenient.

### 3.3 Data Models (extend) — R8, R9

```python
@dataclass
class TechnicalIndicators:
    sma_50:  Optional[float] = None
    sma_150: Optional[float] = None   # NEW (R8)
    sma_200: Optional[float] = None   # NEW (R8)
    sma_200_slope: Optional[float] = None  # NEW (R10)
    week52_high: Optional[float] = None    # NEW (R9)
    week52_low:  Optional[float] = None    # NEW (R9)
    ema_20: Optional[float] = None
    ema_9:  Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    avg_volume_20: Optional[float] = None
    relative_strength: Optional[float] = None   # raw; percentile derived in orchestrator
    rsi_14: Optional[float] = None
    roc_10: Optional[float] = None
    proximity_to_20d_high: Optional[float] = None
```

All new fields are `Optional[float]` → no break to serialization or existing constructors.

**Open Question OQ-2 (gate-result surfacing):** whether to add `passed_hard_filters: bool`,
`regime: MarketRegime`, and `rs_percentile: float` to the API `TickerScore` for UI transparency. Not
assumed here; flagged for decision.

### 3.4 ScoringEngine (modify) — R2, R3, R4, R5, R6, R7

**New method — hard filters (R2):**

```python
def passes_hard_filters(
    self, current_price: float, indicators: TechnicalIndicators
) -> tuple[bool, dict[str, bool]]:
    """Return (all_pass, per_check). Any False → caller assigns score 0.
    H1: current_price > sma_200
    H2: sma_200_slope > 0
    H3: current_price > sma_150
    H4: sma_50 > sma_200
    H5: current_price >= 1.30 * week52_low
    H6: current_price >= 0.75 * week52_high
    Missing indicator (None) for a check ⇒ that check FAILS (conservative)."""
```

**Removed — recovery bonus (R3):** delete the entire `RECOVERY BONUS (0–25 pts)` block from
`calculate_score()`.

**Rewritten — extension penalty + momentum divergence (R4):** cap raised −15 → **−25**; see R4 tiers in
`requirement.md` (distance-above-SMA50 0–10, RSI overbought 0–8, momentum divergence 0–7;
`total_score -= min(penalty, 25)`).

**New parameter — RS percentile (R5):** strength component consumes `rs_percentile` (passed from the
orchestrator) instead of raw RS:

```python
def calculate_score(self, current_price, current_volume, indicators,
                    rs_percentile: float | None = None) -> tuple[int, IndicatorSignals]:
    ...
    # Strength: RS percentile tiers
    if rs_percentile is not None:
        if rs_percentile >= 90: strength_score += 10
        elif rs_percentile >= 70: strength_score += 7
        elif rs_percentile >= 50: strength_score += 4
        # else += 0
```

**New — indicator divergence penalty (R6):** after component scoring, evaluate the four signals
{RSI>50, MACD>signal, ROC>0, price>SMA50}, **counting only signals whose indicator is not `None`**.

```python
signals = []
if indicators.rsi_14 is not None:    signals.append(indicators.rsi_14 > 50)
if indicators.macd_line is not None and indicators.macd_signal is not None:
    signals.append(indicators.macd_line > indicators.macd_signal)
if indicators.roc_10 is not None:    signals.append(indicators.roc_10 > 0)
if indicators.sma_50 is not None:    signals.append(current_price > indicators.sma_50)

if len(signals) >= 2:                       # need ≥2 signals to judge agreement
    bull = sum(signals); bear = len(signals) - bull
    agreement = max(bull, bear) / len(signals)
    if agreement < 0.6:    total_score -= 8   # major disagreement (e.g. 2-2 → 0.5)
    elif agreement <= 0.75: total_score -= 4  # some disagreement (e.g. 3-1 → 0.75)
# else: no penalty
```

> ⚠️ **Correction:** middle tier is `<= 0.75` (not `< 0.75`). With four signals `agreement ∈
> {0.5, 0.75, 1.0}`; a strict `< 0.75` makes the −4 tier unreachable (3-1 splits give exactly 0.75).
> The `None`-aware denominator (`len(signals)`) keeps Property P8 valid (no `None > x` TypeError) and
> means the `/4` in the action plan generalises to `/len(signals)`.

**Score budget (R7):** five 0–20 components (Trend, Momentum, Strength[RSI + RS pct], Confirmation,
Stage2+Pattern) = max 100; penalties Extension (≤−25) + Divergence (≤−8); final clamped to [0, 100].

**Enhanced score:** `calculate_enhanced_score(...)` continues to add the Stage 2 + Pattern bonus (0–20)
on top of `calculate_score`, and must thread `rs_percentile` through.

### 3.5 ScanOrchestrator (modify) — R1, R2, R5, R7

```python
async def execute_scan(self, request, as_of_date=None) -> ScanResponse:
    regime = await self.regime_analyzer.analyze_regime(as_of_date)   # R1 → RegimeResult
    if not regime.emit_signals:                                      # BEARISH
        return ScanResponse(... ranked_tickers=[] ...)               # zero candidates

    # PASS 1: indicators + raw RS for every ticker
    rows = []
    for ticker in universe:
        data = await fetch(... ≥252 bars ...)
        ind  = indicator_calc.calculate_all(data, market_data)
        rows.append((ticker, data, ind))

    # R5: percentile of raw RS across the universe.
    # Precompute a {value -> percentile} rank map (min-rank for ties); avoids O(n^2)
    # .index() lookups and float-identity fragility, and lets us guard None safely.
    rs_values = sorted(r[2].relative_strength for r in rows if r[2].relative_strength is not None)
    rank_map = {v: (i / len(rs_values)) * 100 for i, v in enumerate(rs_values)} if rs_values else {}
    def pct(rs):                      # None or unseen → 0.0 (neutral, no crash)
        return rank_map.get(rs, 0.0)

    # PASS 2: hard-filter gate + scoring + threshold
    scored = []
    for ticker, data, ind in rows:
        ok, _checks = scoring_engine.passes_hard_filters(price, ind)   # R2
        if not ok:
            continue  # score 0 → excluded (a VALID, non-error outcome)
        score, signals, stage, pattern = scoring_engine.calculate_enhanced_score(
            price, volume, ind, data.prices, data.volumes,
            rs_percentile=pct(ind.relative_strength))
        if score >= regime.threshold:                                  # R7
            scored.append(TickerScore(...))

    # NOTE (empty-result semantics): an empty `scored` is a LEGITIMATE result in V3
    # (bearish early-return, or every ticker filtered out / below threshold). The legacy
    # orchestrator guard that raised ScanError("All tickers failed to process") must be
    # REPLACED: raise only when every fetch ERRORED (data unavailable), NOT when tickers
    # were validly filtered out. Distinguish fetch-failure count from filtered-out count.
    return ScanResponse(market_regime=regime.regime,
                        ranked_tickers=ranking_service.rank_tickers(scored), ...)
```

> Whether hard-filter-failed / below-threshold tickers are fully dropped or returned with `score=0`
> is an output-shape decision (OQ-2). Default: **excluded** from `ranked_tickers` (candidates only).

### 3.6 Backtest alignment — V1–V4

`backtest/engine.py` currently labels predicted-bullish as `score >= 70`. V3 BUY logic is
**regime-aware** (`score >= regime.threshold` and `regime != BEARISH`). The backtest's predicted-bullish
definition must use the same regime-aware decision so confusion-matrix metrics reflect the shipped
behavior. Targets/stop (+10%/+20%/−7%) and actual-up definition (`max_gain >= 5%`) are unchanged.

---

## 4. Scoring Architecture (summary table)

| Stage | Element | Effect |
|-------|---------|--------|
| Gate | Regime (R1) | BEARISH ⇒ zero candidates; sets threshold 65/75 |
| Gate | Hard filters H1–H6 (R2) | any fail ⇒ score 0 |
| + | Trend (SMA50+EMA20) | 0–20 |
| + | Momentum (MACD+ROC) | 0–20 |
| + | Strength (RSI + RS percentile) | 0–20 |
| + | Confirmation (Volume+Breakout) | 0–20 |
| + | Stage 2 + Pattern | 0–20 |
| − | Extension penalty (R4) | 0 to −25 |
| − | Divergence penalty (R6) | 0 to −8 |
| Clamp | final | [0, 100] |
| Decision | BUY (R7) | score ≥ threshold AND regime ≠ BEARISH |

---

## 5. Correctness Properties

*Each property is a machine-verifiable statement validated by hypothesis property tests and/or unit
tests. `Validates:` ties it to a requirement.*

### Property P1: Bearish Regime Emits Zero Candidates
*For any* universe and any scores, WHEN the regime gate classifies SPY as BEARISH (not above SMA200 and
last 5 closes below SMA200), the scanner SHALL return an empty `ranked_tickers` list and perform no
per-ticker scoring.
**Validates: R1**

### Property P2: Hard-Filter Failure Forces Score Zero
*For any* ticker that fails at least one of H1–H6, the scanner SHALL exclude it from candidates
(equivalent to `score = 0`), regardless of its component scores.
**Validates: R2**

### Property P3: No Credit Below Moving Averages
*For any* ticker trading below SMA50/SMA150/SMA200, the scoring engine SHALL grant no "recovery" points
and the ticker SHALL be gated out by hard filters (no path yields a BUY).
**Validates: R3**

### Property P4: Extension Penalty Bounded at −25
*For any* indicator set, the extension penalty SHALL be in the range `[−25, 0]` and SHALL never increase
the score; an overextended stock with fading momentum (dist>5% and ROC(10)<−3%) SHALL incur the maximum
applicable **momentum-divergence sub-penalty (+7)** within the extension block (distinct from the R6
indicator-divergence penalty).
**Validates: R4**

### Property P5: RS-Percentile Scoring Is Monotonic
*For any* two tickers A and B in the same scan with `rs_percentile(A) >= rs_percentile(B)`, the RS
contribution to A's strength score SHALL be `>=` B's (tiers: ≥90→10, ≥70→7, ≥50→4, else 0).
**Validates: R5**

### Property P6: Divergence Penalty Thresholds
*For any* combination of the available signals among {RSI>50, MACD>signal, ROC>0, price>SMA50} (counting
only non-`None` indicators, denominator = number available, penalty skipped when fewer than 2), with
`agreement = max(bull,bear)/n`, the engine SHALL subtract exactly 8 when `agreement < 0.6`, exactly 4
when `0.6 <= agreement <= 0.75`, and 0 otherwise. (With all four present, a 2-2 split → −8, a 3-1 split
→ −4, a 4-0 split → 0.)
**Validates: R6**

### Property P7: Regime-Aware BUY Decision
*For any* scored ticker, a BUY SHALL be emitted iff `regime != BEARISH` AND
`score >= regime.threshold` (65 in BULLISH, 75 in NEUTRAL).
**Validates: R7, R1**

### Property P8: Score Bounds
*For any* inputs (including `None` indicators and maximum penalties), the final bullish score SHALL be an
integer in `[0, 100]`.
**Validates: R7, R8**

### Property P9: SMA(200) Slope Sign Correctness
*For any* price series of sufficient length, the computed SMA(200) slope SHALL be `> 0` iff
`SMA200[-1] > SMA200[-1-20]` (rising over the last 20 bars), and `None` when fewer than `200 + 20` bars
are available.
**Validates: R10**

### Property P10: New Indicator Correctness & History Sufficiency
*For any* price series, `sma_150` and `sma_200` SHALL equal the arithmetic mean of the last 150 / 200
closes; `week52_high` / `week52_low` SHALL equal the max / min of the last 252 bars; and ALL of
`sma_200`, `sma_200_slope`, `week52_high`, `week52_low` SHALL be `None` when fewer than the required
bars (200 / 220 / 252) are available. The scan SHALL fetch enough history (≈365 calendar days) that a
valid ticker yields ≥252 trading bars.
**Validates: R8, R9**

> **Coverage check:** R1→P1,P7 · R2→P2 · R3→P3 · R4→P4 · R5→P5 · R6→P6 · R7→P7,P8 · R8→P8,P10 ·
> R9→P10 · R10→P9.

---

## 6. Testing Strategy

**Mandatory testing at four levels.** A task is **incomplete** without (1) **unit tests** for that task,
(2) **integration tests** at component checkpoints, and ultimately (3) the **backtest validation suite**
and (4) **extensive Playwright feature/E2E tests** as the final completion gate. No task is "done"
without its unit tests; the overall V3 work is not "complete" until the Playwright suite passes.

### 6.1 Unit tests (rewrite/extend)
- `test_regime_analyzer.py` — rewrite for `RegimeResult`: BULLISH/BEARISH/NEUTRAL with 5-day
  persistence; boundary (exactly at SMA200; 4-of-5 vs 5-of-5 closes); API-failure → NEUTRAL.
- `test_scoring_engine.py` — rewrite: `passes_hard_filters` each H1–H6 pass/fail (incl. None→fail);
  recovery bonus removed (below-MA stock scores low); extension penalty cap −25 + divergence tiers;
  RS-percentile tiers; divergence penalty thresholds; score clamp [0,100].
- `test_indicator_calculator.py` — extend: SMA150/200 correctness; SMA200 slope sign; 52-week hi/lo;
  insufficient-history → None.

### 6.2 Property tests (hypothesis)
P1–P10 as in §5; minimum 100 iterations each; tag `Feature: v3-high-precision-scanner, Property {N}`.

### 6.3 Backtest validation suite (V1–V4)
- **V1 in-sample** 5 dates, 108 tickers → Precision ≥85%, portfolio >+3%.
- **V2 March 2026** Top 50 → **0 BUYs** (else inspect SPY vs SMA200).
- **V3 out-of-sample** 5 unused dates → Precision ≥80%.
- **V4 portfolio sim** $10k/BUY, 30-day hold → win rate ≥70%, R:R ≥2:1.

### 6.4 Integration tests (backend, pytest — `tests/integration/`)

Run when ≥2 V3 components are wired together (new `tests/integration/test_v3_pipeline.py` + extend
`test_scan_endpoint.py`):

- **IT-1 Regime gate → orchestrator**: mocked BEARISH SPY → `ranked_tickers=[]`,
  `market_regime="bearish"`, no per-ticker scoring; BULLISH SPY proceeds with threshold 65.
- **IT-2 Indicators → hard filters → scoring**: with mocked ≥252-bar data, a ticker failing any H1–H6 is
  excluded; a passing ticker is scored; SMA150/200/slope/52-wk feed the gate.
- **IT-3 Two-pass RS percentile**: a multi-ticker scan ranks leaders above laggards consistently.
- **IT-4 Full `POST /api/v1/scan`**: regime → indicators → hard filters → score → threshold → rank →
  persist → valid `ScanResponse`.
- **IT-5 Backtest endpoints** (`/api/v1/backtest/single`, `/rolling`): regime-aware predicted-bullish
  reaches the confusion matrix; March-2026 single backtest → 0 predicted-bullish.

### 6.6 Comprehensive backtest + optimal-threshold report (V2-style, at scale)

Beyond the focused V1–V4 suite, a large-scale backtest reproduces the V2 reporting workflow for V3
(`backend/generate_report.py` → `backtest_report.html`, `backend/error_analysis.py`):

- **Universe:** full halal list (hundreds — `ALL_HALAL_STOCKS.txt` / `halal_stocks_usa.md`, 371), batched
  to the 5-concurrent Polygon limit.
- **Dates:** many across regimes (in-sample 5 + OOS 5 + March-2026 control + extra bull/bear/neutral
  months), ideally via `/api/v1/backtest/rolling` (monthly, 2024–2026).
- **Optimization:** sweep score threshold (50→90) × gain threshold (3%→10%); tabulate
  precision/recall/F1/portfolio per cell; pick the optimum **on in-sample only**, then report its OOS
  performance (anti-overfit). Confirm regime thresholds 65/75 sit near the in-sample optimum.
- **Output:** regenerated `backtest_report.html` (per-period confusion matrix, P&L, threshold×gain
  heatmap, optimal point, in-sample vs OOS) + a written threshold recommendation. Sweep/aggregation math
  is unit-tested on synthetic trades (no live-data dependency for the math).

Implemented by **task 4.6**.

### 6.5 Feature / E2E tests (Playwright — `frontend/tests/e2e/`) — FINAL COMPLETION GATE

**Extensive Playwright feature testing is the final gate: V3 is not "complete" until the full
backend+frontend stack passes these against a live server.** Extends the existing suite
(`happy-path`, `error-scenarios`, `loading-states`, `results-display`, `comprehensive-test`).

⚠️ **Setup reality (must be fixed first — task 5.1):** `frontend/playwright.config.ts` currently
**only starts vite**, NOT the backend — its `webServer` must become an array that also launches
`uvicorn main:app --port 8000` (with `POLYGON_TOKEN`). Components have **no `data-testid`s** and the UI
has **no bearish/0-trades empty-state copy** today; 5.1 adds these. Every test captures screenshots to
`frontend/test-results/screenshots/`.

**Determinism:** the Live Scanner sends only tickers (no `as_of_date`) so regime is *live* and cannot be
forced bearish reliably; force determinism via the **Backtest tab (fixed past date, e.g. 2026-03-01)** or
**`page.route` fixtures**. `MarketRegimeBadge` renders the literal **"Bearish Market"**; Cloudscape
`Slider`s must be driven by keyboard (`ArrowRight`), not `.fill()`.

New V3 feature specs (`frontend/tests/e2e/`):

- **`v3-bearish-regime.spec.ts`** — deterministic via `page.route` mock OR backtest tab → assert the
  literal **"Bearish Market"** badge + the empty-state copy (added in 5.1), not a red error. Screenshots:
  badge, empty state.
- **`v3-hard-filters.spec.ts`** — `page.route` a `ScanResponse` with known weak+strong tickers → weak
  (below-MA) absent, leaders present, ranked descending; shown tickers have green SMA50 badge and
  `score >= threshold` (no hard-coded live ticker names).
- **`v3-backtest-metrics.spec.ts`** — click **Backtest tab**; run a single-date backtest; assert
  confusion matrix + Precision/Recall/F1 cards render; drive sliders by keyboard (`ArrowRight`) and assert
  a metric value **changes** (structural, not a hard-coded %).
- **`v3-march-2026.spec.ts`** — Backtest tab, date `2026-03-01`, Top 50 → assert **no qualifying (★)
  trades**: the 0-trades empty state, or a confusion matrix with TP=0 and FP=0. (UI has no "BUY" label.)
- **`v3-regression.spec.ts`** — core happy-path with V3 active asserting V3 invariants (regime badge
  present; every shown ticker `score >= threshold`), not a verbatim happy-path re-run.

**Feature-gate done criteria:** all e2e specs (existing + V3) pass with 0 failures, screenshots
generated, `npx playwright show-report` clean. Only then are all tasks complete.

---

## 7. Backward Compatibility / Migration

| Change | Ripple | Mitigation |
|--------|--------|-----------|
| `analyze_regime` → `RegimeResult` (R1) | orchestrator, `test_regime_analyzer.py` | update call sites + tests |
| Recovery bonus removed (R3) | broad score shifts; `test_scoring_engine.py` | rewrite affected expectations |
| New `TechnicalIndicators` fields (R8–R10) | constructors/serialization | all optional → no break |
| RS percentile two-pass (R5) | orchestrator loop restructured | encapsulate in PASS 1 / PASS 2 |
| Regime-aware BUY (R7) | `backtest/engine.py` predicted-bullish | align definition (§3.6) |

---

## 8. Open Questions

- **OQ-1 (history length, R9): RESOLVED → binding fix.** `fetch_stock_data(days=N)` is calendar-based;
  `days=250` ≈ 178 trading bars (insufficient). Raise to **≈365 calendar days** at all call sites and
  assert ≥252 trading bars before gate computation. See §3.2 and requirement.md R9. No longer open.
- **OQ-2 (output shape):** Surface `passed_hard_filters` / `regime` / `rs_percentile` on `TickerScore`
  for the UI, or keep candidates-only? Default: candidates-only, no API model change. *(Still open —
  product decision.)*
- **OQ-3 (EMA21 role):** The action plan says "EMA21 + 200-day gate." Is EMA21 part of the gate decision
  or an auxiliary trend reading? Default: SPY-vs-SMA200 + 5-day persistence drives the gate; EMA21
  computed for context. *(Still open — confirm with author.)*
